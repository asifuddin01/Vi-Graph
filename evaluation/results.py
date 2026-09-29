"""What an evaluation run writes: run info (§18.1) and one result per sample."""

from __future__ import annotations

import gzip
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from app.pipeline.analyze import RunMetadata
from evaluation.metrics.scores import SampleScores
from evaluation.metrics.structural_qa import QuestionOutcome
from evaluation.predictors import Prediction
from evaluation.samples import SplitInfo

RUN_FILE = "run.json"
PREDICTIONS_FILE = "predictions.jsonl"
PREDICTIONS_ARCHIVE = "predictions.jsonl.gz"
SUMMARY_FILE = "summary.json"
REPORT_FILE = "report.md"


class RunConfig(BaseModel):
    """Everything that decides a run's outputs; a resumed run must match it exactly."""

    dataset: str  # directory
    split: str
    limit: int | None
    predictor: str  # "vlm:hf", "vlm:mock", "oracle", ...
    model_id: str | None = None
    revision: str | None = None
    adapter: str | None = None
    dtype: str | None = None
    temperature: float = 0.0
    top_p: float = 1.0
    max_new_tokens: int = 4096
    seed: int = 0
    image_max_side: int
    image_max_pixels: int


class RunInfo(BaseModel):
    name: str
    created_at: datetime
    completed_at: datetime | None = None
    command: list[str]
    config: RunConfig
    split: SplitInfo
    metadata: RunMetadata | None = None  # §18.1, from the pipeline (VLM predictors)
    adapter_config: dict[str, object] | None = None  # LoRA rank, alpha, target modules …
    versions: dict[str, object]  # app, schema, matching, scores, QA benchmark, git, packages
    environment: dict[str, object]  # python, platform, GPU
    samples_done: int = 0
    errors: int = 0


class SampleResult(BaseModel):
    sample_id: str
    attributes: dict[str, str | int]
    prediction: Prediction
    scores: SampleScores
    first_attempt_scores: SampleScores  # attempt 1 as-is (ablation §24D)
    qa: list[QuestionOutcome]


def read_run(run_dir: Path) -> RunInfo:
    return RunInfo.model_validate_json((run_dir / RUN_FILE).read_text())


def read_results(run_dir: Path) -> list[SampleResult]:
    """Results from predictions.jsonl, or the committed gzipped copy when that is absent."""
    plain, archive = run_dir / PREDICTIONS_FILE, run_dir / PREDICTIONS_ARCHIVE
    if plain.exists():
        text = plain.read_text()
    elif archive.exists():
        text = gzip.decompress(archive.read_bytes()).decode()
    else:
        raise FileNotFoundError(f"no {PREDICTIONS_FILE} or {PREDICTIONS_ARCHIVE} in {run_dir}")
    return [SampleResult.model_validate_json(line) for line in text.splitlines() if line.strip()]
