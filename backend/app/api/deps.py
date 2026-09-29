"""Shared FastAPI dependencies. Tests replace them via ``app.dependency_overrides``."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.api.limits import SlidingWindowLimiter
from app.config import Settings, get_settings
from app.storage.images import ImageStore
from app.storage.runs import RunStore
from app.vlm.base import VLMBackend
from app.vlm.factory import get_vlm_backend


@lru_cache
def get_run_store() -> RunStore:
    return RunStore(get_settings().storage_dir / "vigraph.sqlite3")


@lru_cache
def get_image_store() -> ImageStore:
    return ImageStore(get_settings().storage_dir / "images")


@lru_cache
def get_analyze_limiter() -> SlidingWindowLimiter:
    return SlidingWindowLimiter(get_settings().analyze_rate_limit_per_minute)


@lru_cache
def get_qa_limiter() -> SlidingWindowLimiter:
    return SlidingWindowLimiter(get_settings().qa_rate_limit_per_minute)


def _enforce(request: Request, limiter: SlidingWindowLimiter, what: str) -> None:
    client = request.client.host if request.client else "unknown"
    retry_after = limiter.retry_after(client)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail=f"too many {what} requests; try again shortly",
            headers={"Retry-After": str(max(1, round(retry_after)))},
        )


def enforce_analyze_rate_limit(
    request: Request,
    limiter: Annotated[SlidingWindowLimiter, Depends(get_analyze_limiter)],
) -> None:
    _enforce(request, limiter, "analysis")


def enforce_qa_rate_limit(
    request: Request,
    limiter: Annotated[SlidingWindowLimiter, Depends(get_qa_limiter)],
) -> None:
    _enforce(request, limiter, "question")


SettingsDep = Annotated[Settings, Depends(get_settings)]
VLMDep = Annotated[VLMBackend, Depends(get_vlm_backend)]
RunStoreDep = Annotated[RunStore, Depends(get_run_store)]
ImageStoreDep = Annotated[ImageStore, Depends(get_image_store)]
