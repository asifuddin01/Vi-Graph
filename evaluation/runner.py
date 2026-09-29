"""Run a predictor over a dataset split and score it (spec §20, §18.1).

A run directory holds ``run.json`` (config, split hash, §18.1 metadata, versions),
``predictions.jsonl`` (one result per sample, appended and fsynced as it goes), and, once
the split is done, ``summary.json``, ``report.md`` and ``predictions.jsonl.gz``.

Runs resume: calling ``run_evaluation`` again with the same config on the same directory
skips finished samples, so a Colab disconnect costs at most one sample. A different config
is refused. Samples whose predictor raised are recorded as failures (and count as such);
``retry_errors`` re-runs them. After ``max_consecutive_errors`` failures in a row the run
stops — something is wrong with the setup, not with the samples.
"""

from __future__ import annotations

import contextlib
import gzip
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from app import __version__
from app.schemas import SCHEMA_VERSION, DiagramGraph
from evaluation.aggregate import summarize
from evaluation.metrics.matching import match_graphs, matching_config
from evaluation.metrics.scores import SCORES_VERSION, score_sample
from evaluation.metrics.structural_qa import (
    QA_BENCHMARK_VERSION,
    generate_questions,
    score_questions,
)
from evaluation.predictors import Prediction, Predictor
from evaluation.report import render_report
from evaluation.results import (
    PREDICTIONS_ARCHIVE,
    PREDICTIONS_FILE,
    REPORT_FILE,
    RUN_FILE,
    SUMMARY_FILE,
    RunConfig,
    RunInfo,
    SampleResult,
    read_results,
)
from evaluation.samples import EvalSample, SplitInfo


class RunConfigMismatch(ValueError):
    pass


class TooManyErrors(RuntimeError):
    pass


def run_evaluation(
    predictor: Predictor,
    samples: list[EvalSample],
    split: SplitInfo,
    config: RunConfig,
    out_dir: Path,
    *,
    name: str | None = None,
    command: list[str] | None = None,
    retry_errors: bool = False,
    max_consecutive_errors: int = 3,
    adapter_config: dict[str, object] | None = None,
    progress: bool = True,
) -> dict[str, object]:
    """Evaluate ``samples`` (already limited to ``config.limit``); returns the summary."""
    out_dir.mkdir(parents=True, exist_ok=True)
    run_path = out_dir / RUN_FILE
    if run_path.exists():
        run = RunInfo.model_validate_json(run_path.read_text())
        if run.config != config:
            raise RunConfigMismatch(
                f"{out_dir} holds a run with a different config; use another output directory"
            )
        if run.split.split_hash != split.split_hash:
            raise RunConfigMismatch(
                f"{out_dir} was run on a different build of split {split.split!r} "
                f"(hash {run.split.split_hash[:12]}, now {split.split_hash[:12]})"
            )
    else:
        run = RunInfo(
            name=name or out_dir.name,
            created_at=datetime.now(UTC),
            command=command or sys.argv,
            config=config,
            split=split,
            adapter_config=adapter_config,
            predictor_info=predictor.describe(),
            versions=_versions(),
            environment=_environment(),
        )
        _write(run_path, run.model_dump_json(indent=2))

    done = _load_done(out_dir / PREDICTIONS_FILE, drop_errors=retry_errors)
    todo = [s for s in samples if s.id not in done]
    consecutive_errors = 0
    start = time.perf_counter()
    with (out_dir / PREDICTIONS_FILE).open("a") as handle:
        for index, sample in enumerate(todo, 1):
            result = evaluate_sample(predictor, sample)
            handle.write(result.model_dump_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            consecutive_errors = consecutive_errors + 1 if result.prediction.error else 0
            if progress:
                _progress(index, len(todo), len(done), start, result)
            if consecutive_errors >= max_consecutive_errors:
                raise TooManyErrors(
                    f"{consecutive_errors} samples in a row failed with an error (last: "
                    f"{result.prediction.error}). Fix the setup, then resume with "
                    "retry_errors / --retry-errors."
                )

    results = _order(read_results(out_dir), samples)
    metadata = predictor.run_metadata()
    if metadata is not None:
        run.metadata = metadata
    run.samples_done = len(results)
    run.errors = sum(r.prediction.error is not None for r in results)
    run.completed_at = datetime.now(UTC)
    _write(run_path, run.model_dump_json(indent=2))
    return finalize(out_dir, run, results)


def finalize(out_dir: Path, run: RunInfo, results: list[SampleResult]) -> dict[str, object]:
    """Write summary.json, report.md and the gzipped predictions (for committing)."""
    summary = summarize(results)
    _write(out_dir / SUMMARY_FILE, json.dumps(summary, indent=2) + "\n")
    _write(out_dir / REPORT_FILE, render_report(run, summary))
    lines = "".join(r.model_dump_json() + "\n" for r in results)
    (out_dir / PREDICTIONS_ARCHIVE).write_bytes(gzip.compress(lines.encode(), mtime=0))
    return summary


def rescore(out_dir: Path, samples: list[EvalSample]) -> dict[str, object]:
    """Re-score stored predictions with the current scoring code (after a SCORES_VERSION or
    QA_BENCHMARK_VERSION bump) — no model calls."""
    run = RunInfo.model_validate_json((out_dir / RUN_FILE).read_text())
    by_id = {s.id: s for s in samples}
    results = [
        score_prediction(by_id[r.sample_id], r.prediction)
        for r in _order(read_results(out_dir), samples)
    ]
    _write(out_dir / PREDICTIONS_FILE, "".join(r.model_dump_json() + "\n" for r in results))
    run.versions = {**run.versions, **_score_versions()}
    _write(out_dir / RUN_FILE, run.model_dump_json(indent=2))
    return finalize(out_dir, run, results)


def evaluate_sample(predictor: Predictor, sample: EvalSample) -> SampleResult:
    started = time.perf_counter()
    try:
        prediction = predictor.predict(sample)
    except Exception as exc:  # recorded as a failed sample; the run continues
        prediction = Prediction(
            graph=None,
            first_attempt_graph=None,
            validity=None,
            analysis=None,
            latency_ms=(time.perf_counter() - started) * 1000,
            error=f"{type(exc).__name__}: {exc}",
        )
    return score_prediction(sample, prediction)


def score_prediction(sample: EvalSample, prediction: Prediction) -> SampleResult:
    ground_truth = DiagramGraph.model_validate_json(sample.graph.read_text())
    match = match_graphs(prediction.graph, ground_truth) if prediction.graph else None
    return SampleResult(
        sample_id=sample.id,
        attributes=sample.attributes,
        prediction=prediction,
        scores=score_sample(prediction.graph, ground_truth),
        first_attempt_scores=score_sample(prediction.first_attempt_graph, ground_truth),
        qa=score_questions(generate_questions(ground_truth, sample.id), prediction.graph, match),
    )


def _load_done(path: Path, *, drop_errors: bool) -> set[str]:
    """Ids already evaluated. A truncated last line (killed mid-write) is removed; with
    ``drop_errors``, failed-with-error samples are removed so they run again."""
    if not path.exists():
        return set()
    kept: list[str] = []
    done: set[str] = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            result = SampleResult.model_validate_json(line)
        except ValueError:
            continue  # the partial line of an interrupted write
        if drop_errors and result.prediction.error:
            continue
        kept.append(line)
        done.add(result.sample_id)
    _write(path, "".join(f"{line}\n" for line in kept))
    return done


def _order(results: list[SampleResult], samples: list[EvalSample]) -> list[SampleResult]:
    position = {s.id: i for i, s in enumerate(samples)}
    latest = {r.sample_id: r for r in results if r.sample_id in position}
    return sorted(latest.values(), key=lambda r: position[r.sample_id])


def _progress(index: int, total: int, skipped: int, start: float, result: SampleResult) -> None:
    elapsed = time.perf_counter() - start
    eta = elapsed / index * (total - index)
    status = result.prediction.error or (
        result.prediction.validity.status if result.prediction.validity else "done"
    )
    print(
        f"[{index}/{total}{f' +{skipped} done before' if skipped else ''}] {result.sample_id} "
        f"{status} node F1 {result.scores.nodes.f1:.2f} edge F1 {result.scores.edges.f1:.2f} "
        f"· {elapsed / 60:.1f} min elapsed, ~{eta / 60:.1f} min left",
        flush=True,
    )


def _write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def _versions() -> dict[str, object]:
    packages = {}
    for package in (
        "pydantic",
        "networkx",
        "rapidfuzz",
        "scipy",
        "torch",
        "transformers",
        "peft",
        "opencv-python-headless",
        "pytesseract",
    ):
        with contextlib.suppress(PackageNotFoundError):
            packages[package] = version(package)
    return {
        "app": __version__,
        "schema": SCHEMA_VERSION,
        **_score_versions(),
        "git_commit": _git_commit(),
        "packages": packages,
    }


def _score_versions() -> dict[str, object]:
    return {
        "matching": matching_config()["matching_version"],
        "scores": SCORES_VERSION,
        "qa_benchmark": QA_BENCHMARK_VERSION,
        "matching_config": matching_config(),
    }


def _git_commit() -> str | None:
    try:
        root = Path(__file__).resolve().parents[1]
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return commit + ("-dirty" if dirty else "")


def _environment() -> dict[str, object]:
    environment: dict[str, object] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import torch  # optional: only present where models run

        if torch.cuda.is_available():
            environment["gpu"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    return environment
