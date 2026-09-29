"""The VLM interface every model backend implements (spec §33.3).

Backends only turn a conversation into text. Prompting, JSON validation, retry and repair
live in the pipeline, so they behave identically for every model — which the multi-model
comparison (§19) depends on.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from PIL.Image import Image
from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class Message:
    """One conversation turn. Only user turns may carry images."""

    role: Literal["user", "assistant"]
    text: str
    images: tuple[Image, ...] = ()


class DecodingParams(BaseModel):
    """Decoding settings; logged with every inference call (§18.1)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    temperature: float = Field(default=0.0, ge=0.0)  # 0.0 = greedy decoding
    top_p: float = Field(default=1.0, gt=0.0, le=1.0)
    max_new_tokens: int = Field(default=4096, ge=1)
    seed: int = 0


class ModelInfo(BaseModel):
    """Which model produced an output (§18.1: model name + checkpoint/revision)."""

    model_config = ConfigDict(frozen=True)

    backend: str
    model_id: str
    revision: str | None = None
    adapter_path: str | None = None


class Completion(BaseModel):
    """What a backend returns from a single generation."""

    text: str
    # "length" means generation hit max_new_tokens — a common cause of truncated JSON.
    finish_reason: Literal["stop", "length"] | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class VLMOutput(Completion):
    """A completion plus everything needed to reproduce it."""

    latency_ms: float
    model: ModelInfo
    params: DecodingParams


class VLMBackend(ABC):
    @property
    @abstractmethod
    def info(self) -> ModelInfo: ...

    @abstractmethod
    def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion: ...

    def generate(
        self, messages: Sequence[Message], params: DecodingParams | None = None
    ) -> VLMOutput:
        params = params or DecodingParams()
        validate_conversation(messages)
        start = time.perf_counter()
        completion = self._generate(messages, params)
        latency_ms = (time.perf_counter() - start) * 1000
        return VLMOutput(
            **completion.model_dump(), latency_ms=latency_ms, model=self.info, params=params
        )


def validate_conversation(messages: Sequence[Message]) -> None:
    """Require alternating turns that start and end with the user; images on user turns only."""
    if not messages:
        raise ValueError("conversation is empty")
    for index, message in enumerate(messages):
        expected = "user" if index % 2 == 0 else "assistant"
        if message.role != expected:
            raise ValueError(
                f"message #{index} has role '{message.role}'; turns must alternate "
                "user/assistant starting with user"
            )
        if message.images and message.role != "user":
            raise ValueError(f"message #{index} is an assistant turn but carries images")
    if messages[-1].role != "user":
        raise ValueError("conversation must end with a user turn")
