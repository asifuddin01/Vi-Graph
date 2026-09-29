"""Application settings, loaded from environment variables (prefix ``VIGRAPH_``).

A ``.env`` file at the repository root is read if present; real environment
variables take precedence over it. See ``.env.example`` for every option.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VIGRAPH_",
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )

    env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    # Comma-separated in the environment, e.g. "http://localhost:3000,https://x.dev".
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # Uploads, results, and the SQLite DB. Kept outside any executable/static path (§29).
    storage_dir: Path = REPO_ROOT / "storage"
    max_upload_mb: int = 10

    # Stage A preprocessing (§8). Images are only ever downscaled, and only when the
    # longest side exceeds image_max_side. image_max_pixels guards against
    # decompression bombs and is checked before the image is decoded.
    image_max_side: int = Field(default=2048, ge=64)
    image_max_pixels: int = Field(default=40_000_000, ge=1)

    # VLM backend selection — the single swap point (§33.3).
    vlm_backend: Literal["mock", "hf"] = "mock"
    vlm_model_id: str = "Qwen/Qwen3-VL-2B-Instruct"
    vlm_adapter_path: Path | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("vlm_adapter_path", mode="before")
    @classmethod
    def _empty_path_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
