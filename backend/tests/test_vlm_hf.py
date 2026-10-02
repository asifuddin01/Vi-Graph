"""HuggingFaceVLM tests with a fake model/processor (numpy stands in for torch tensors).

Real inference is not exercised here: this environment cannot download weights or install
torch. These tests cover everything around the model call.
"""

import importlib.util
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from app.vlm import DecodingParams, HuggingFaceVLM, Message
from app.vlm.hf import HFRuntime, generation_kwargs, to_chat_messages

PROMPT_TOKENS = 7


class FakeBatch(dict):
    def to(self, device: str) -> "FakeBatch":
        self.device = device
        return self


class FakeProcessor:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.template_calls: list[tuple[list[dict], dict]] = []
        self.decoded: list[list[int]] = []

    def apply_chat_template(self, chat: list[dict], **kwargs: Any) -> FakeBatch:
        self.template_calls.append((chat, kwargs))
        return FakeBatch(input_ids=np.zeros((1, PROMPT_TOKENS), dtype=int))

    def decode(self, ids: np.ndarray, skip_special_tokens: bool) -> str:
        assert skip_special_tokens
        self.decoded.append(ids.tolist())
        return self.reply


class FakeModel:
    device = "cuda:0"

    def __init__(self, state: dict, new_tokens: int) -> None:
        self.state = state
        self.new_tokens = new_tokens
        self.generate_calls: list[dict] = []

    def generate(self, **kwargs: Any) -> np.ndarray:
        assert self.state["inference_mode"], "generate must run inside inference_mode"
        self.generate_calls.append(kwargs)
        new = np.arange(100, 100 + self.new_tokens)[None, :]
        return np.concatenate([kwargs["input_ids"], new], axis=1)


@pytest.fixture
def state() -> dict:
    return {"inference_mode": False, "seeds": []}


def make_backend(state: dict, *, new_tokens: int = 5, reply: str = '{"ok": true}') -> tuple:
    @contextmanager
    def inference_mode() -> Iterator[None]:
        state["inference_mode"] = True
        yield
        state["inference_mode"] = False

    model = FakeModel(state, new_tokens)
    processor = FakeProcessor(reply)
    runtime = HFRuntime(
        model=model,
        processor=processor,
        inference_mode=inference_mode,
        set_seed=state["seeds"].append,
        revision="abc123",
    )
    backend = HuggingFaceVLM("Qwen/Qwen3-VL-2B-Instruct", revision="main", runtime=runtime)
    return backend, model, processor


def image() -> Image.Image:
    return Image.new("RGB", (32, 32), "white")


# --- pure helpers ---------------------------------------------------------------------


def test_chat_messages_put_images_before_text() -> None:
    first, second = image(), image()

    chat = to_chat_messages(
        [
            Message(role="user", text="Reconstruct.", images=(first, second)),
            Message(role="assistant", text="not json"),
            Message(role="user", text="Fix it."),
        ]
    )

    assert chat == [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": first},
                {"type": "image", "image": second},
                {"type": "text", "text": "Reconstruct."},
            ],
        },
        {"role": "assistant", "content": [{"type": "text", "text": "not json"}]},
        {"role": "user", "content": [{"type": "text", "text": "Fix it."}]},
    ]


def test_greedy_decoding_kwargs() -> None:
    kwargs = generation_kwargs(DecodingParams(max_new_tokens=512))

    assert kwargs == {"max_new_tokens": 512, "repetition_penalty": 1.0, "do_sample": False}


def test_sampling_kwargs_override_model_defaults() -> None:
    kwargs = generation_kwargs(DecodingParams(temperature=0.7, top_p=0.9))

    assert kwargs["do_sample"] is True
    assert (kwargs["temperature"], kwargs["top_p"]) == (0.7, 0.9)
    assert kwargs["top_k"] == 0  # disables a model's own top-k default
    assert kwargs["repetition_penalty"] == 1.0


# --- generation path ------------------------------------------------------------------


def test_generate_returns_decoded_new_tokens_with_counts(state: dict) -> None:
    backend, model, processor = make_backend(state, new_tokens=5, reply='{"nodes": []}')

    output = backend.generate([Message(role="user", text="Go", images=(image(),))])

    assert output.text == '{"nodes": []}'
    assert output.prompt_tokens == PROMPT_TOKENS
    assert output.completion_tokens == 5
    assert output.finish_reason == "stop"
    assert processor.decoded == [[100, 101, 102, 103, 104]]  # prompt tokens excluded


def test_generate_applies_template_device_seed_and_params(state: dict) -> None:
    backend, model, processor = make_backend(state)
    params = DecodingParams(temperature=0.5, top_p=0.95, max_new_tokens=64, seed=11)

    backend.generate([Message(role="user", text="Go", images=(image(),))], params)

    chat, template_kwargs = processor.template_calls[0]
    assert chat[0]["content"][-1] == {"type": "text", "text": "Go"}
    assert template_kwargs == {
        "tokenize": True,
        "add_generation_prompt": True,
        "return_dict": True,
        "return_tensors": "pt",
    }
    assert state["seeds"] == [11]
    call = model.generate_calls[0]
    assert "input_ids" in call
    assert {k: call[k] for k in generation_kwargs(params)} == generation_kwargs(params)
    assert not state["inference_mode"]


def test_inputs_are_moved_to_model_device(state: dict) -> None:
    backend, model, processor = make_backend(state)
    moved: list[str] = []
    original = processor.apply_chat_template

    def spy(chat: list[dict], **kwargs: Any) -> FakeBatch:
        batch = original(chat, **kwargs)
        real_to = batch.to

        def to(device: str) -> FakeBatch:
            moved.append(device)
            return real_to(device)

        batch.to = to  # type: ignore[method-assign]
        return batch

    processor.apply_chat_template = spy  # type: ignore[method-assign]

    backend.generate([Message(role="user", text="Go")])

    assert moved == ["cuda:0"]


def test_hitting_max_new_tokens_reports_length(state: dict) -> None:
    backend, _, _ = make_backend(state, new_tokens=16)

    output = backend.generate([Message(role="user", text="Go")], DecodingParams(max_new_tokens=16))

    assert output.finish_reason == "length"


# --- runaway guard --------------------------------------------------------------------


class StreamingProcessor(FakeProcessor):
    """Token k (from 100) decodes to node k: '{"nodes":[' + one node object per token."""

    def decode(self, ids: np.ndarray, skip_special_tokens: bool) -> str:
        nodes = "".join(f'{{"id":"n{k}","label":"Shard {k}"}},' for k in range(len(ids)))
        return '{"nodes":[' + nodes


class SteppingModel(FakeModel):
    """Generates one token at a time and asks the stopping criteria after each, like
    transformers does; ``stopping_criteria`` here is the plain predicate list."""

    def generate(self, **kwargs: Any) -> np.ndarray:
        self.generate_calls.append(kwargs)
        ids = kwargs["input_ids"]
        for step in range(kwargs["max_new_tokens"]):
            ids = np.concatenate([ids, [[100 + step]]], axis=1)
            if any(stop(ids) for stop in kwargs.get("stopping_criteria", [])):
                break
        return ids


def guarded_backend(state: dict, *, criteria: bool = True) -> tuple:
    backend, _, _ = make_backend(state)
    runtime = backend._runtime
    runtime.model = SteppingModel(state, 0)
    runtime.processor = StreamingProcessor("")
    runtime.inference_mode = lambda: contextmanager(lambda: iter([None]))()
    runtime.stopping_criteria = (lambda predicate: [predicate]) if criteria else None
    return backend, runtime.model


def test_runaway_guard_stops_a_looping_generation(state: dict) -> None:
    backend, model = guarded_backend(state)

    output = backend.generate(
        [Message(role="user", text="Go")],
        DecodingParams(max_new_tokens=200, runaway_guard="1"),
    )

    # checked every 16 tokens: 48 nodes is below the 50-node floor, 64 fires
    assert output.completion_tokens == 64
    assert output.finish_reason == "runaway"
    assert output.runaway.startswith("node loop: 64 nodes")
    assert output.params.runaway_guard == "1"


def test_without_the_guard_nothing_is_passed_to_generate(state: dict) -> None:
    backend, model = guarded_backend(state)

    output = backend.generate([Message(role="user", text="Go")], DecodingParams(max_new_tokens=80))

    assert "stopping_criteria" not in model.generate_calls[0]
    assert (output.completion_tokens, output.finish_reason, output.runaway) == (80, "length", None)


def test_guard_needs_a_runtime_that_supports_it(state: dict) -> None:
    backend, _ = guarded_backend(state, criteria=False)

    with pytest.raises(RuntimeError, match="runaway guard"):
        backend.generate([Message(role="user", text="Go")], DecodingParams(runaway_guard="1"))


# --- model identity -------------------------------------------------------------------


def test_info_reports_resolved_revision_once_loaded(state: dict) -> None:
    backend, _, _ = make_backend(state)

    assert backend.info.backend == "hf"
    assert backend.info.model_id == "Qwen/Qwen3-VL-2B-Instruct"
    assert backend.info.revision == "abc123"


def test_info_before_loading_reports_requested_revision_and_adapter() -> None:
    backend = HuggingFaceVLM("org/vlm", revision="v2", adapter_path=Path("adapters/run-1"))

    assert not backend.loaded
    assert backend.info.revision == "v2"
    assert backend.info.adapter_path == "adapters/run-1"


@pytest.mark.skipif(
    importlib.util.find_spec("torch") is not None, reason="only meaningful without torch"
)
def test_missing_vlm_dependencies_give_an_actionable_error() -> None:
    backend = HuggingFaceVLM("org/vlm")

    with pytest.raises(RuntimeError, match="requirements-vlm.txt"):
        backend.generate([Message(role="user", text="Go")])
