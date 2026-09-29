"""The full diagram → graph pipeline (spec §8, Stages A–D) with run metadata (§18.1)."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from app import __version__
from app.pipeline.extraction import ExtractionResult, extract_graph
from app.pipeline.normalize import NormalizationResult, normalize_graph
from app.schemas import SCHEMA_VERSION, DiagramGraph
from app.utils.images import preprocess_image
from app.vlm.base import DecodingParams, ModelInfo, VLMBackend


class ImageInfo(BaseModel):
    sha256: str  # of the uploaded bytes
    format: str
    original_size: tuple[int, int]
    size: tuple[int, int]  # as sent to the model


class RunMetadata(BaseModel):
    """Everything spec §18.1 requires to reproduce an inference run."""

    app_version: str
    schema_version: str
    model: ModelInfo
    params: DecodingParams
    prompt_id: str
    prompt_sha256: str
    correction_prompt_id: str
    correction_prompt_sha256: str
    split_version: str | None = None  # dataset split hash, for evaluation runs


class AnalysisRecord(BaseModel):
    id: str
    created_at: datetime
    metadata: RunMetadata
    image: ImageInfo
    extraction: ExtractionResult
    normalization: NormalizationResult | None  # None when extraction failed
    latency_ms: float

    @property
    def graph(self) -> DiagramGraph | None:
        return self.normalization.graph if self.normalization else None


def analyze_image(
    vlm: VLMBackend,
    data: bytes,
    *,
    max_side: int,
    max_pixels: int,
    params: DecodingParams | None = None,
    split_version: str | None = None,
) -> AnalysisRecord:
    """Run Stages A–D on one image. Raises ``ImageError`` for unacceptable images."""
    start = time.perf_counter()
    params = params or DecodingParams()
    prepared = preprocess_image(data, max_side=max_side, max_pixels=max_pixels)
    extraction = extract_graph(vlm, [prepared.image], params)
    normalization = normalize_graph(extraction.graph) if extraction.graph else None

    return AnalysisRecord(
        id=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        metadata=RunMetadata(
            app_version=__version__,
            schema_version=SCHEMA_VERSION,
            # Taken after generation, so a lazily loaded model reports its resolved revision.
            model=extraction.attempts[-1].output.model,
            params=params,
            prompt_id=extraction.prompt_id,
            prompt_sha256=extraction.prompt_sha256,
            correction_prompt_id=extraction.correction_prompt_id,
            correction_prompt_sha256=extraction.correction_prompt_sha256,
            split_version=split_version,
        ),
        image=ImageInfo(
            sha256=prepared.sha256,
            format=prepared.format,
            original_size=prepared.original_size,
            size=prepared.image.size,
        ),
        extraction=extraction,
        normalization=normalization,
        latency_ms=(time.perf_counter() - start) * 1000,
    )
