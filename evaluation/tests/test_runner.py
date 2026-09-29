import gzip
import json
from pathlib import Path

import pytest

from app.exporters.graphviz import graphviz_available
from app.pipeline.analyze import RunMetadata
from app.vlm.base import DecodingParams
from app.vlm.mock import MockVLM
from data.generator.dataset import build_dataset, default_config
from evaluation.__main__ import main as cli
from evaluation.aggregate import summarize
from evaluation.predictors import OraclePredictor, Prediction, Predictor, VLMPredictor
from evaluation.results import RunConfig, read_results, read_run
from evaluation.runner import RunConfigMismatch, TooManyErrors, run_evaluation
from evaluation.samples import EvalSample, SplitError, SplitInfo, load_split

pytestmark = pytest.mark.skipif(not graphviz_available(), reason="Graphviz not installed")

LIMITS = {"image_max_side": 2048, "image_max_pixels": 40_000_000}


@pytest.fixture(scope="module")
def dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("eval-data")
    build_dataset(default_config("tiny", seed=3, train=0, val=0, test=8), out, workers=4)
    return out


def config(dataset: Path, **overrides: object) -> RunConfig:
    return RunConfig(
        dataset=str(dataset), split="test", limit=None, predictor="test", **LIMITS
    ).model_copy(update=overrides)


def oracle(split: SplitInfo) -> OraclePredictor:
    return OraclePredictor(DecodingParams(), split_version=split.split_hash, **LIMITS)


class Counting(Predictor):
    """Wraps a predictor; records calls and can raise for chosen samples."""

    def __init__(self, inner: Predictor, fail: set[str] = frozenset()) -> None:
        self.inner, self.fail, self.calls = inner, set(fail), []
        self.name = "test"

    def predict(self, sample: EvalSample) -> Prediction:
        self.calls.append(sample.id)
        if sample.id in self.fail:
            raise RuntimeError("CUDA out of memory")
        return self.inner.predict(sample)

    def run_metadata(self) -> RunMetadata | None:
        return self.inner.run_metadata()


# --- whole runs through the CLI -------------------------------------------------------


def test_oracle_run_scores_perfectly_and_logs_metadata(dataset: Path, tmp_path: Path) -> None:
    out = tmp_path / "oracle"

    assert (
        cli(["run", "--dataset", str(dataset), "--backend", "oracle", "--out", str(out), "--quiet"])
        == 0
    )

    summary = json.loads((out / "summary.json").read_text())
    for metric in (
        "node_f1",
        "edge_f1",
        "edge_strict_f1",
        "graph_similarity",
        "qa_accuracy",
        "valid_bare_json",
    ):
        assert summary["macro"][metric]["mean"] == 1.0, metric
    assert summary["samples"] == 8 and summary["errors"] == 0
    run = read_run(out)
    split, _ = load_split(dataset, "test")
    assert run.metadata.split_version == split.split_hash == run.split.split_hash
    assert run.metadata.prompt_id == "graph_extraction@1"
    assert run.versions["scores"] == "1" and run.versions["matching"] == "1"
    assert run.completed_at is not None and run.samples_done == 8
    report = (out / "report.md").read_text()
    assert "| Node F1 | 1.000 |" in report and split.split_hash in report
    archived = gzip.decompress((out / "predictions.jsonl.gz").read_bytes()).decode()
    assert archived == (out / "predictions.jsonl").read_text()


def test_mock_run_and_limit(dataset: Path, tmp_path: Path) -> None:
    out = tmp_path / "mock"

    cli(
        [
            "run",
            "--dataset",
            str(dataset),
            "--backend",
            "mock",
            "--limit",
            "3",
            "--out",
            str(out),
            "--quiet",
        ]
    )

    results = read_results(out)
    assert [r.sample_id for r in results] == ["test-000000", "test-000001", "test-000002"]
    assert all(r.prediction.analysis.metadata.model.backend == "mock" for r in results)
    assert read_run(out).config.model_id is None  # only recorded for real models


def test_summarize_and_rescore_reproduce_the_summary(dataset: Path, tmp_path: Path) -> None:
    out = tmp_path / "run"
    cli(
        [
            "run",
            "--dataset",
            str(dataset),
            "--backend",
            "mock",
            "--limit",
            "4",
            "--out",
            str(out),
            "--quiet",
        ]
    )
    first = json.loads((out / "summary.json").read_text())

    (out / "predictions.jsonl").unlink()  # summarize falls back to the committed archive
    assert cli(["summarize", str(out)]) == 0
    assert json.loads((out / "summary.json").read_text()) == first
    assert cli(["rescore", str(out)]) == 0
    assert json.loads((out / "summary.json").read_text()) == first


# --- resuming -------------------------------------------------------------------------


def test_resume_skips_finished_samples_and_drops_a_torn_line(dataset: Path, tmp_path: Path) -> None:
    split, samples = load_split(dataset, "test")
    out = tmp_path / "resume"
    run_evaluation(oracle(split), samples[:3], split, config(dataset), out, progress=False)
    lines = (out / "predictions.jsonl").read_text().splitlines()
    (out / "predictions.jsonl").write_text(lines[0] + "\n" + lines[1] + "\n" + lines[2][:100])

    counting = Counting(oracle(split))
    summary = run_evaluation(counting, samples, split, config(dataset), out, progress=False)

    assert counting.calls == [s.id for s in samples[2:]]
    assert summary["samples"] == 8
    assert [r.sample_id for r in read_results(out)] == [s.id for s in samples]


def test_resume_refuses_a_different_config_or_split_build(dataset: Path, tmp_path: Path) -> None:
    split, samples = load_split(dataset, "test")
    out = tmp_path / "refuse"
    run_evaluation(oracle(split), samples[:1], split, config(dataset), out, progress=False)

    with pytest.raises(RunConfigMismatch, match="different config"):
        run_evaluation(oracle(split), samples[:1], split, config(dataset, temperature=0.7), out)
    rebuilt = split.model_copy(update={"split_hash": "0" * 64})
    with pytest.raises(RunConfigMismatch, match="different build"):
        run_evaluation(oracle(split), samples[:1], rebuilt, config(dataset), out)


# --- errors ---------------------------------------------------------------------------


def test_errors_are_recorded_as_failures_and_can_be_retried(dataset: Path, tmp_path: Path) -> None:
    split, samples = load_split(dataset, "test")
    out = tmp_path / "errors"
    flaky = Counting(oracle(split), fail={"test-000001", "test-000004"})

    summary = run_evaluation(flaky, samples, split, config(dataset), out, progress=False)

    assert summary["errors"] == 2
    assert summary["macro"]["node_f1"]["mean"] == pytest.approx(6 / 8)
    failed = {r.sample_id: r for r in read_results(out) if r.prediction.error}
    assert failed["test-000001"].prediction.error == "RuntimeError: CUDA out of memory"
    assert not failed["test-000001"].scores.has_graph

    fixed = Counting(oracle(split))
    summary = run_evaluation(
        fixed, samples, split, config(dataset), out, retry_errors=True, progress=False
    )

    assert fixed.calls == ["test-000001", "test-000004"]
    assert summary["errors"] == 0 and summary["macro"]["node_f1"]["mean"] == 1.0
    assert read_run(out).errors == 0


def test_consecutive_errors_stop_the_run(dataset: Path, tmp_path: Path) -> None:
    split, samples = load_split(dataset, "test")
    broken = Counting(oracle(split), fail={s.id for s in samples})

    with pytest.raises(TooManyErrors, match="--retry-errors"):
        run_evaluation(broken, samples, split, config(dataset), tmp_path / "x", progress=False)

    assert len(broken.calls) == 3


# --- what gets scored -----------------------------------------------------------------


class DuplicateEdgeOracle(OraclePredictor):
    """The ground truth with its first edge written twice: normalization removes the
    duplicate, so only the first-attempt (raw) graph is penalized (ablation §24D)."""

    def predict(self, sample: EvalSample) -> Prediction:
        gt = json.loads(sample.graph.read_text())
        gt["edges"].append(gt["edges"][0])
        self.oracle.next_response = json.dumps(gt)
        return VLMPredictor.predict(self, sample)


def test_first_attempt_scores_measure_the_raw_output(dataset: Path, tmp_path: Path) -> None:
    split, samples = load_split(dataset, "test")
    predictor = DuplicateEdgeOracle(DecodingParams(), split_version=split.split_hash, **LIMITS)

    summary = run_evaluation(
        predictor, samples[:4], split, config(dataset), tmp_path / "d", progress=False
    )

    assert summary["macro"]["edge_f1"]["mean"] == 1.0
    assert summary["macro"]["first_attempt_edge_f1"]["mean"] < 1.0
    assert summary["macro"]["first_attempt_node_f1"]["mean"] == 1.0


def test_fenced_output_is_valid_but_not_bare_json(dataset: Path, tmp_path: Path) -> None:
    split, samples = load_split(dataset, "test")
    gt = samples[0].graph.read_text()
    vlm = MockVLM([f"Here you go:\n```json\n{gt}\n```"])
    predictor = VLMPredictor(vlm, DecodingParams(), split_version=split.split_hash, **LIMITS)

    summary = run_evaluation(
        predictor, samples[:1], split, config(dataset), tmp_path / "f", progress=False
    )

    assert summary["macro"]["valid_first_attempt"]["mean"] == 1.0
    assert summary["macro"]["valid_bare_json"]["mean"] == 0.0
    assert summary["macro"]["node_f1"]["mean"] == 1.0


def test_summary_counts_failures_as_zero_and_skips_undefined_metrics(
    dataset: Path, tmp_path: Path
) -> None:
    split, samples = load_split(dataset, "test")
    run_evaluation(
        Counting(oracle(split), fail={"test-000000"}),
        samples[:2],
        split,
        config(dataset),
        tmp_path / "s",
        progress=False,
    )

    summary = summarize(read_results(tmp_path / "s"))

    assert summary["macro"]["node_f1"] == {
        "mean": 0.5,
        "std": pytest.approx(0.7071, abs=1e-4),
        "n": 2,
    }
    assert summary["macro"]["label_accuracy"]["n"] == 1  # undefined for the failure
    assert summary["macro"]["valid_first_attempt"]["n"] == 1  # the error had no model output
    assert summary["breakdowns"]["level"]["1"]["samples"] == 1
    assert list(summary["breakdowns"]) == ["level", "diagram_type", "layout", "theme"]


# --- split verification ---------------------------------------------------------------


def test_split_files_are_verified(dataset: Path, tmp_path: Path) -> None:
    copy = tmp_path / "copy"
    copy.mkdir()
    for item in dataset.iterdir():
        if item.is_dir():
            (copy / item.name).mkdir()
            for f in item.iterdir():
                (copy / item.name / f.name).write_bytes(f.read_bytes())
        else:
            (copy / item.name).write_bytes(item.read_bytes())
    graph = copy / "graphs" / "test-000002.json"
    gt = json.loads(graph.read_text())
    gt["diagram_type"] = "other" if gt["diagram_type"] != "other" else "uml"
    graph.write_text(json.dumps(gt))

    with pytest.raises(SplitError, match="test-000002: ground-truth hash mismatch"):
        load_split(copy, "test")
    with pytest.raises(SplitError, match="no samples"):
        load_split(dataset, "val")
