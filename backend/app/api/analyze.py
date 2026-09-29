"""POST /api/analyze and GET /api/analyses/{diagram_id} (spec §28)."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import (
    ImageStoreDep,
    RunStoreDep,
    SettingsDep,
    VLMDep,
    enforce_analyze_rate_limit,
)
from app.exporters.mermaid import to_mermaid
from app.pipeline.analyze import AnalysisRecord, ImageInfo, analyze_image, build_run_metadata
from app.pipeline.extraction import ExtractionStatus
from app.pipeline.normalize import NormalizationChange
from app.pipeline.repair import RepairFix
from app.schemas import DiagramGraph
from app.utils.images import ImageError
from app.vlm.base import DecodingParams, ModelInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])

_DIAGRAM_ID = re.compile(r"[0-9a-f]{32}")


class AttemptView(BaseModel):
    number: int
    valid: bool
    json_method: str | None
    problems: list[str]
    raw_output: str
    finish_reason: str | None
    latency_ms: float


class AnalyzeMetrics(BaseModel):
    latency_ms: float
    attempts: int
    repairs: int
    normalization_changes: int
    nodes: int | None
    edges: int | None
    cached: bool


class AnalyzeResponse(BaseModel):
    diagram_id: str
    schema_version: str
    status: ExtractionStatus
    graph: DiagramGraph | None
    mermaid: str | None  # Mermaid flowchart of the graph (§10); None when there is none
    metrics: AnalyzeMetrics
    attempts: list[AttemptView]
    repairs: list[RepairFix]
    normalization_changes: list[NormalizationChange]
    failure_reason: str | None
    model: ModelInfo
    image: ImageInfo
    created_at: datetime


def to_response(record: AnalysisRecord, *, cached: bool) -> AnalyzeResponse:
    extraction = record.extraction
    graph = record.graph
    changes = record.normalization.changes if record.normalization else []
    return AnalyzeResponse(
        diagram_id=record.id,
        schema_version=record.metadata.schema_version,
        status=extraction.status,
        graph=graph,
        mermaid=to_mermaid(graph) if graph else None,
        metrics=AnalyzeMetrics(
            latency_ms=record.latency_ms,
            attempts=len(extraction.attempts),
            repairs=len(extraction.repairs),
            normalization_changes=len(changes),
            nodes=len(graph.nodes) if graph else None,
            edges=len(graph.edges) if graph else None,
            cached=cached,
        ),
        attempts=[
            AttemptView(
                number=attempt.number,
                valid=attempt.valid,
                json_method=attempt.json_method,
                problems=attempt.problems,
                raw_output=attempt.output.text,
                finish_reason=attempt.output.finish_reason,
                latency_ms=attempt.output.latency_ms,
            )
            for attempt in extraction.attempts
        ],
        repairs=extraction.repairs,
        normalization_changes=changes,
        failure_reason=extraction.failure_reason,
        model=record.metadata.model,
        image=record.image,
        created_at=record.created_at,
    )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    dependencies=[Depends(enforce_analyze_rate_limit)],
)
def analyze(
    file: Annotated[UploadFile, File(description="Diagram image: PNG, JPEG, or WebP")],
    settings: SettingsDep,
    vlm: VLMDep,
    runs: RunStoreDep,
    images: ImageStoreDep,
    model: Annotated[str | None, Form(description="Model id; defaults to the server's")] = None,
) -> AnalyzeResponse:
    if model is not None and model != vlm.info.model_id:
        raise HTTPException(
            status_code=422,
            detail=f"model {model!r} is not available (available: {vlm.info.model_id})",
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)  # the upload's filename is never used
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"file is larger than {settings.max_upload_mb} MB"
        )

    params = DecodingParams()
    if params.temperature == 0.0:
        # Greedy decoding is deterministic, so an identical earlier run can be reused (§30).
        metadata = build_run_metadata(vlm.info, params, image_max_side=settings.image_max_side)
        cached = runs.find_cached(hashlib.sha256(data).hexdigest(), metadata)
        if cached is not None:
            return to_response(cached, cached=True)

    try:
        record = analyze_image(
            vlm,
            data,
            max_side=settings.image_max_side,
            max_pixels=settings.image_max_pixels,
            params=params,
        )
    except ImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.exception("VLM backend failed")
        raise HTTPException(
            status_code=503, detail="the model backend failed; see the server logs"
        ) from exc

    images.save(data, record.image.sha256, record.image.format)
    runs.save(record)
    return to_response(record, cached=False)


@router.get("/analyses/{diagram_id}", response_model=AnalyzeResponse)
def get_analysis(diagram_id: str, runs: RunStoreDep) -> AnalyzeResponse:
    record = runs.get(diagram_id) if _DIAGRAM_ID.fullmatch(diagram_id) else None
    if record is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return to_response(record, cached=False)
