"""FastAPI entrypoint.

Run from ``backend/``:  ``uvicorn app.main:app --reload``
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.analyze import router as analyze_router
from app.api.export import router as export_router
from app.api.health import router as health_router
from app.api.limits import BodySizeLimitMiddleware
from app.api.qa import router as qa_router
from app.config import Settings, get_settings

# Room for multipart framing around an upload of the maximum allowed size.
_MULTIPART_OVERHEAD_BYTES = 64 * 1024


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(title="Vi-Graph API", version=__version__)
    app.add_middleware(
        BodySizeLimitMiddleware,
        max_bytes=settings.max_upload_mb * 1024 * 1024 + _MULTIPART_OVERHEAD_BYTES,
    )
    # Added last, so it is outermost and error responses (e.g. 413) carry CORS headers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(analyze_router)
    app.include_router(export_router)
    app.include_router(qa_router)
    return app


app = create_app()
