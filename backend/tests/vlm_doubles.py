"""VLM test doubles."""

from collections.abc import Sequence

from app.vlm import DecodingParams, Message
from app.vlm.base import Completion, ModelInfo, VLMBackend


class RecordingVLM(VLMBackend):
    """A stand-in vision model that answers with a fixed reply and records its inputs."""

    def __init__(self, reply: str = "The encoder boxes are drawn in blue.") -> None:
        self.reply = reply
        self.calls: list[list[Message]] = []

    @property
    def info(self) -> ModelInfo:
        return ModelInfo(backend="test", model_id="recording-vlm")

    def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion:
        self.calls.append(list(messages))
        return Completion(text=self.reply, finish_reason="stop")


class ExplodingVLM(VLMBackend):
    """A vision model whose every call fails, as a GPU running out of memory would."""

    @property
    def info(self) -> ModelInfo:
        return ModelInfo(backend="test", model_id="exploding")

    def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion:
        raise RuntimeError("CUDA out of memory (secret internal detail)")
