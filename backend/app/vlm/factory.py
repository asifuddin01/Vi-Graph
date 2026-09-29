"""Backend selection from settings — the single swap point for model/checkpoint (§33.3)."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.vlm.base import VLMBackend
from app.vlm.hf import HuggingFaceVLM
from app.vlm.mock import MockVLM


def create_vlm_backend(settings: Settings) -> VLMBackend:
    if settings.vlm_backend == "mock":
        return MockVLM()
    if settings.vlm_backend == "hf":
        # Weights load lazily on first use (or via .load()), not here.
        return HuggingFaceVLM(
            settings.vlm_model_id,
            revision=settings.vlm_revision,
            adapter_path=settings.vlm_adapter_path,
            dtype=settings.vlm_dtype,
            device_map=settings.vlm_device_map,
        )
    raise ValueError(f"unknown VLM backend {settings.vlm_backend!r}")


@lru_cache
def get_vlm_backend() -> VLMBackend:
    """Process-wide backend instance, so model weights load once (§30)."""
    return create_vlm_backend(get_settings())
