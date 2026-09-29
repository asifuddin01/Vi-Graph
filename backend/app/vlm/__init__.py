"""Thin VLM interface: the single swap point for model/checkpoint (spec §33.3)."""

from app.vlm.base import (
    Completion,
    DecodingParams,
    Message,
    ModelInfo,
    VLMBackend,
    VLMOutput,
    validate_conversation,
)
from app.vlm.factory import create_vlm_backend, get_vlm_backend
from app.vlm.mock import MockVLM

__all__ = [
    "Completion",
    "DecodingParams",
    "Message",
    "MockVLM",
    "ModelInfo",
    "VLMBackend",
    "VLMOutput",
    "create_vlm_backend",
    "get_vlm_backend",
    "validate_conversation",
]
