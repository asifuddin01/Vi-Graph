import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from PIL import Image
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas import DiagramGraph
from app.vlm import (
    DecodingParams,
    Message,
    MockVLM,
    create_vlm_backend,
    get_vlm_backend,
    validate_conversation,
)
from app.vlm.mock import MOCK_MODEL_ID

FIXTURES = Path(__file__).parent / "fixtures"


def image() -> Image.Image:
    return Image.new("RGB", (64, 32), "white")


def user(text: str = "Reconstruct this diagram.", with_image: bool = False) -> Message:
    return Message(role="user", text=text, images=(image(),) if with_image else ())


def assistant(text: str = "{}") -> Message:
    return Message(role="assistant", text=text)


# --- decoding params ------------------------------------------------------------------


def test_default_decoding_is_greedy() -> None:
    params = DecodingParams()

    assert (params.temperature, params.top_p, params.seed) == (0.0, 1.0, 0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"temperature": -0.1},
        {"top_p": 0.0},
        {"top_p": 1.1},
        {"max_new_tokens": 0},
        {"beam_width": 4},
    ],
)
def test_invalid_decoding_params_are_rejected(kwargs: dict) -> None:
    with pytest.raises(ValidationError):
        DecodingParams(**kwargs)


def test_decoding_params_are_immutable() -> None:
    params = DecodingParams()

    with pytest.raises(ValidationError):
        params.temperature = 0.7


# --- conversation rules ---------------------------------------------------------------


def test_single_user_turn_with_image_is_valid() -> None:
    validate_conversation([user(with_image=True)])


def test_corrective_retry_conversation_is_valid() -> None:
    validate_conversation([user(with_image=True), assistant("not json"), user("Fix: ...")])


@pytest.mark.parametrize(
    ("messages", "error"),
    [
        ([], "empty"),
        ([assistant()], "role 'assistant'"),
        ([user(), user()], "role 'user'"),
        ([user(), assistant()], "end with a user turn"),
    ],
    ids=["empty", "starts-with-assistant", "not-alternating", "ends-with-assistant"],
)
def test_invalid_conversations_are_rejected(messages: list[Message], error: str) -> None:
    with pytest.raises(ValueError, match=error):
        validate_conversation(messages)


def test_images_on_assistant_turn_are_rejected() -> None:
    bad = Message(role="assistant", text="x", images=(image(),))

    with pytest.raises(ValueError, match="carries images"):
        validate_conversation([user(), bad, user()])


# --- mock backend ---------------------------------------------------------------------


def test_mock_default_response_is_the_spec_example_graph() -> None:
    output = MockVLM().generate([user(with_image=True)])

    assert json.loads(output.text) == json.loads((FIXTURES / "graph_v2_example.json").read_text())
    DiagramGraph.model_validate_json(output.text)


def test_output_carries_model_info_params_and_latency() -> None:
    params = DecodingParams(temperature=0.2, top_p=0.9, seed=7)

    output = MockVLM().generate([user()], params)

    assert output.params == params
    assert output.model.backend == "mock"
    assert output.model.model_id == MOCK_MODEL_ID
    assert output.model.revision is not None
    assert output.latency_ms >= 0
    assert output.finish_reason == "stop"


def test_default_params_are_used_when_omitted() -> None:
    assert MockVLM().generate([user()]).params == DecodingParams()


def test_output_serializes_for_logging() -> None:
    dumped = MockVLM().generate([user()]).model_dump(mode="json")

    assert {"text", "finish_reason", "latency_ms", "model", "params"} <= dumped.keys()
    json.dumps(dumped)


def test_scripted_responses_play_in_order_then_last_repeats() -> None:
    vlm = MockVLM(["first", "second"])

    texts = [vlm.generate([user()]).text for _ in range(4)]

    assert texts == ["first", "second", "second", "second"]
    assert vlm.call_count == 4


def test_calls_are_recorded() -> None:
    vlm = MockVLM()

    vlm.generate([user(with_image=True), assistant("bad"), user("Fix edge n3->n9")])

    assert [m.role for m in vlm.calls[-1]] == ["user", "assistant", "user"]
    assert vlm.calls[-1][-1].text == "Fix edge n3->n9"


def test_call_log_is_bounded() -> None:
    vlm = MockVLM()

    for _ in range(100):
        vlm.generate([user()])

    assert vlm.call_count == 100
    assert len(vlm.calls) == 64


def test_invalid_conversation_never_reaches_the_backend() -> None:
    vlm = MockVLM()

    with pytest.raises(ValueError):
        vlm.generate([assistant()])

    assert vlm.call_count == 0


# --- factory --------------------------------------------------------------------------


def test_factory_builds_mock_backend() -> None:
    backend = create_vlm_backend(Settings(_env_file=None, vlm_backend="mock"))

    assert isinstance(backend, MockVLM)


def test_factory_reports_hf_backend_as_not_implemented_yet() -> None:
    with pytest.raises(NotImplementedError, match="VIGRAPH_VLM_BACKEND=mock"):
        create_vlm_backend(Settings(_env_file=None, vlm_backend="hf"))


@pytest.fixture
def fresh_caches() -> Iterator[None]:
    get_settings.cache_clear()
    get_vlm_backend.cache_clear()
    yield
    get_settings.cache_clear()
    get_vlm_backend.cache_clear()


def test_backend_instance_is_shared_per_process(
    fresh_caches: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIGRAPH_VLM_BACKEND", "mock")

    assert get_vlm_backend() is get_vlm_backend()
