"""Predictors: image → predicted graph, for evaluation runs.

``VLMPredictor`` runs the app's own pipeline (``analyze_image``, spec §8 Stages A–D), so
evaluation scores the system users get. ``OraclePredictor`` answers with the ground truth
through the same pipeline: every score must come out perfect, which checks the evaluation
path end to end. It is a sanity check, never a result.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from pydantic import BaseModel

from app.pipeline.analyze import AnalysisRecord, RunMetadata, analyze_image
from app.pipeline.extraction import ExtractionResult
from app.pipeline.json_extract import extract_json_object
from app.schemas import DiagramGraph
from app.vlm.base import Completion, DecodingParams, Message, ModelInfo, VLMBackend
from evaluation.metrics.scores import Validity, validity
from evaluation.samples import EvalSample


class Prediction(BaseModel):
    graph: DiagramGraph | None  # the pipeline's final graph (validated, repaired, normalized)
    # Attempt 1 exactly as the model wrote it, when it was a valid graph: no retry, repair or
    # normalization (the "raw output" side of ablation §24D).
    first_attempt_graph: DiagramGraph | None
    validity: Validity | None  # VLM predictors only
    analysis: AnalysisRecord | None  # VLM predictors: every attempt's raw output, repairs, …
    latency_ms: float
    error: str | None = None  # the predictor raised; the sample counts as failed


class Predictor(ABC):
    name: str

    @abstractmethod
    def predict(self, sample: EvalSample) -> Prediction: ...

    def run_metadata(self) -> RunMetadata | None:
        """§18.1 metadata, once known (after the first prediction for lazily loaded models)."""
        return None


class VLMPredictor(Predictor):
    def __init__(
        self,
        vlm: VLMBackend,
        params: DecodingParams,
        *,
        image_max_side: int,
        image_max_pixels: int,
        split_version: str,
    ) -> None:
        self.vlm = vlm
        self.params = params
        self.image_max_side = image_max_side
        self.image_max_pixels = image_max_pixels
        self.split_version = split_version
        self.name = f"vlm:{vlm.info.backend}"
        self._metadata: RunMetadata | None = None

    def predict(self, sample: EvalSample) -> Prediction:
        record = analyze_image(
            self.vlm,
            sample.image.read_bytes(),
            max_side=self.image_max_side,
            max_pixels=self.image_max_pixels,
            params=self.params,
            split_version=self.split_version,
        )
        self._metadata = record.metadata
        return Prediction(
            graph=record.graph,
            first_attempt_graph=first_attempt_graph(record.extraction),
            validity=validity(record.extraction),
            analysis=record,
            latency_ms=record.latency_ms,
        )

    def run_metadata(self) -> RunMetadata | None:
        return self._metadata


def first_attempt_graph(extraction: ExtractionResult) -> DiagramGraph | None:
    first = extraction.attempts[0]
    if not first.valid:
        return None
    value, _ = extract_json_object(first.output.text)
    return DiagramGraph.model_validate(value)


class OracleVLM(VLMBackend):
    """Replies with whatever ``next_response`` holds (set per sample by OraclePredictor)."""

    def __init__(self) -> None:
        self.next_response: str | None = None

    @property
    def info(self) -> ModelInfo:
        return ModelInfo(backend="oracle", model_id="ground-truth")

    def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion:
        if self.next_response is None:
            raise RuntimeError("OracleVLM has no response set")
        return Completion(text=self.next_response, finish_reason="stop")


class OraclePredictor(VLMPredictor):
    def __init__(
        self,
        params: DecodingParams,
        *,
        image_max_side: int,
        image_max_pixels: int,
        split_version: str,
    ) -> None:
        self.oracle = OracleVLM()
        super().__init__(
            self.oracle,
            params,
            image_max_side=image_max_side,
            image_max_pixels=image_max_pixels,
            split_version=split_version,
        )

    def predict(self, sample: EvalSample) -> Prediction:
        self.oracle.next_response = sample.graph.read_text()
        try:
            return super().predict(sample)
        finally:
            self.oracle.next_response = None
