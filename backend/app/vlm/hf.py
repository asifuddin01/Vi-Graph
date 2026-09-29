"""Hugging Face ``transformers`` backend for image-text-to-text models (Qwen3-VL by default).

Works with any model ``AutoModelForImageTextToText`` can load, which is what the multi-model
comparison (§19) needs. torch/transformers/peft are imported lazily, so this module imports
without them; install ``requirements-vlm.txt`` to actually run it. An optional LoRA adapter
from a Colab training run (§18) is applied with peft.

Decoding is fully determined by ``DecodingParams``: model-provided generation defaults that
would silently change the output (sampling top_k, repetition_penalty) are overridden, so
the logged parameters are the real ones (§18.1) and every model runs the same protocol.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.vlm.base import Completion, DecodingParams, Message, ModelInfo, VLMBackend


@dataclass
class HFRuntime:
    """A loaded model and processor, plus the torch hooks generation needs."""

    model: Any
    processor: Any
    inference_mode: Callable[[], AbstractContextManager[Any]]
    set_seed: Callable[[int], None]
    revision: str | None  # resolved commit hash when known


def to_chat_messages(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """Our conversation → the chat-template format of transformers processors."""
    chat: list[dict[str, Any]] = []
    for message in messages:
        content: list[dict[str, Any]] = [{"type": "image", "image": img} for img in message.images]
        content.append({"type": "text", "text": message.text})
        chat.append({"role": message.role, "content": content})
    return chat


def generation_kwargs(params: DecodingParams) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"max_new_tokens": params.max_new_tokens, "repetition_penalty": 1.0}
    if params.temperature == 0.0:
        kwargs["do_sample"] = False
    else:
        # top_k=0 disables top-k filtering; otherwise a model's default (e.g. 20) would apply.
        kwargs.update(do_sample=True, temperature=params.temperature, top_p=params.top_p, top_k=0)
    return kwargs


def load_runtime(
    model_id: str,
    *,
    revision: str | None,
    adapter_path: Path | None,
    dtype: str,
    device_map: str,
) -> HFRuntime:
    try:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor, set_seed
    except ImportError as exc:
        raise RuntimeError(
            "The 'hf' VLM backend needs the packages in requirements-vlm.txt "
            "(pip install -r requirements-vlm.txt)."
        ) from exc

    processor = AutoProcessor.from_pretrained(model_id, revision=revision)
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, revision=revision, dtype=dtype, device_map=device_map
    )
    resolved_revision = getattr(model.config, "_commit_hash", None) or revision

    if adapter_path is not None:
        try:
            from peft import PeftModel
        except ImportError as exc:
            raise RuntimeError("Loading a LoRA adapter needs peft (requirements-vlm.txt).") from exc
        model = PeftModel.from_pretrained(model, str(adapter_path))

    model.eval()
    return HFRuntime(
        model=model,
        processor=processor,
        inference_mode=torch.inference_mode,
        set_seed=set_seed,
        revision=resolved_revision,
    )


class HuggingFaceVLM(VLMBackend):
    def __init__(
        self,
        model_id: str,
        *,
        revision: str | None = None,
        adapter_path: Path | None = None,
        dtype: str = "auto",
        device_map: str = "auto",
        runtime: HFRuntime | None = None,
    ) -> None:
        self.model_id = model_id
        self.revision = revision
        self.adapter_path = adapter_path
        self.dtype = dtype
        self.device_map = device_map
        self._runtime = runtime  # injected in tests; otherwise loaded on first use
        self._load_lock = threading.Lock()
        # One generation at a time: the model lives on a single device.
        self._generate_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._runtime is not None

    @property
    def info(self) -> ModelInfo:
        revision = self._runtime.revision if self._runtime else self.revision
        return ModelInfo(
            backend="hf",
            model_id=self.model_id,
            revision=revision,
            adapter_path=str(self.adapter_path) if self.adapter_path else None,
        )

    def load(self) -> HFRuntime:
        with self._load_lock:
            if self._runtime is None:
                self._runtime = load_runtime(
                    self.model_id,
                    revision=self.revision,
                    adapter_path=self.adapter_path,
                    dtype=self.dtype,
                    device_map=self.device_map,
                )
            return self._runtime

    def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion:
        runtime = self.load()
        with self._generate_lock:
            inputs = runtime.processor.apply_chat_template(
                to_chat_messages(messages),
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            ).to(runtime.model.device)
            runtime.set_seed(params.seed)
            with runtime.inference_mode():
                output_ids = runtime.model.generate(**inputs, **generation_kwargs(params))

        prompt_tokens = int(inputs["input_ids"].shape[1])
        new_ids = output_ids[0, prompt_tokens:]
        completion_tokens = int(new_ids.shape[0])
        text = runtime.processor.decode(new_ids, skip_special_tokens=True)
        return Completion(
            text=text,
            finish_reason="length" if completion_tokens >= params.max_new_tokens else "stop",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
