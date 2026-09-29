"""Backend selection from settings — the single swap point for model/checkpoint (§33.3)."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.vlm.base import VLMBackend
from app.vlm.mock import MockVLM


def create_vlm_backend(settings: Settings) -> VLMBackend:
    if settings.vlm_backend == "mock":
        return MockVLM()
    if settings.vlm_backend == "hf":
        raise NotImplementedError(
            "The Hugging Face VLM backend is not implemented yet (Phase 1, step 5). "
            "Set VIGRAPH_VLM_BACKEND=mock."
        )
    raise ValueError(f"unknown VLM backend {settings.vlm_backend!r}")


@lru_cache
def get_vlm_backend() -> VLMBackend:
    """Process-wide backend instance, so model weights load once (§30)."""
    return create_vlm_backend(get_settings())
