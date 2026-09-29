"""A FastAPI test environment: the real app with temporary stores and a scripted VLM."""

import io
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_analyze_limiter, get_image_store, get_qa_limiter, get_run_store
from app.api.limits import SlidingWindowLimiter
from app.config import Settings, get_settings
from app.main import create_app
from app.storage.images import ImageStore
from app.storage.runs import RunStore
from app.vlm import MockVLM
from app.vlm.base import VLMBackend
from app.vlm.factory import get_vlm_backend


@dataclass
class Env:
    app: FastAPI
    client: TestClient
    vlm: VLMBackend
    runs: RunStore
    images: ImageStore


def make_env(
    tmp_path: Path,
    vlm: VLMBackend | None = None,
    *,
    rate_limit: int = 0,
    qa_rate_limit: int = 0,
    max_upload_mb: int = 1,
) -> Env:
    settings = Settings(
        _env_file=None,
        storage_dir=tmp_path,
        max_upload_mb=max_upload_mb,
        analyze_rate_limit_per_minute=rate_limit,
        image_max_side=512,
    )
    vlm = vlm or MockVLM()
    runs = RunStore(tmp_path / "runs.sqlite3")
    images = ImageStore(tmp_path / "images")
    limiter = SlidingWindowLimiter(rate_limit)
    qa_limiter = SlidingWindowLimiter(qa_rate_limit)
    app = create_app(settings)
    app.dependency_overrides.update(
        {
            get_settings: lambda: settings,
            get_vlm_backend: lambda: vlm,
            get_run_store: lambda: runs,
            get_image_store: lambda: images,
            get_analyze_limiter: lambda: limiter,
            get_qa_limiter: lambda: qa_limiter,
        }
    )
    return Env(app=app, client=TestClient(app), vlm=vlm, runs=runs, images=images)


def png(color: str = "white", size: tuple[int, int] = (800, 400)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def upload(env: Env, data: bytes, filename: str = "diagram.png", **form: str):
    return env.client.post("/api/analyze", files={"file": (filename, data, "image/png")}, data=form)
