import json
from pathlib import Path

import pytest

from app.exporters.graphviz import graphviz_available
from app.vlm.base import DecodingParams
from data.generator.dataset import build_dataset, default_config
from evaluation.__main__ import main as cli
from evaluation.compare import IncompatibleRuns, compare_conditions, load_runs, seed_summary
from evaluation.predictors import OraclePredictor, Prediction, VLMPredictor
from evaluation.results import RunConfig
from evaluation.runner import run_evaluation
from evaluation.samples import EvalSample, load_split

pytestmark = pytest.mark.skipif(not graphviz_available(), reason="Graphviz not installed")

LIMITS = {"image_max_side": 2048, "image_max_pixels": 40_000_000}


class DropLastEdge(OraclePredictor):
    """The ground truth minus its last edge: a strictly worse condition on edges only."""

    def predict(self, sample: EvalSample) -> Prediction:
        gt = json.loads(sample.graph.read_text())
        gt["edges"] = gt["edges"][:-1]
        self.oracle.next_response = json.dumps(gt)
        return VLMPredictor.predict(self, sample)


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("compare")
    dataset = root / "data"
    build_dataset(default_config("tiny", seed=4, train=0, val=0, test=12), dataset, workers=4)
    split, samples = load_split(dataset, "test")
    base = RunConfig(dataset=str(dataset), split="test", limit=None, predictor="test", **LIMITS)
    made = {}
    for name, cls, seed in [
        ("oracle-s0", OraclePredictor, 0),
        ("oracle-s1", OraclePredictor, 1),
        ("drop-s0", DropLastEdge, 0),
        ("drop-s1", DropLastEdge, 1),
    ]:
        params = DecodingParams(seed=seed)
        predictor = cls(params, split_version=split.split_hash, **LIMITS)
        config = base.model_copy(update={"seed": seed, "predictor": name.split("-")[0]})
        run_evaluation(predictor, samples, split, config, root / name, progress=False)
        made[name] = root / name
    short = root / "oracle-short"
    run_evaluation(
        OraclePredictor(DecodingParams(), split_version=split.split_hash, **LIMITS),
        samples[:5],
        split,
        base.model_copy(update={"limit": 5, "predictor": "oracle"}),
        short,
        progress=False,
    )
    made["oracle-short"] = short
    return made


def test_seed_summary(runs: dict[str, Path]) -> None:
    summary = seed_summary(load_runs([runs["drop-s0"], runs["drop-s1"]]))

    assert summary.seeds == [0, 1] and summary.samples == 12
    assert summary.metrics["node_f1"] == {"mean": 1.0, "std": 0.0}
    assert summary.metrics["edge_f1"]["mean"] < 1.0
    assert summary.metrics["edge_f1"]["std"] == 0.0  # the same predictions under both seeds
    assert set(summary.by_level) == {"1", "2", "3", "4"}
    assert summary.by_level["1"]["edge_f1"]["mean"] < summary.by_level["4"]["edge_f1"]["mean"]


def test_seed_summary_refuses_different_conditions(runs: dict[str, Path]) -> None:
    with pytest.raises(IncompatibleRuns, match="more than the seed"):
        seed_summary(load_runs([runs["oracle-s0"], runs["drop-s1"]]))
    with pytest.raises(IncompatibleRuns, match="different samples"):
        seed_summary(load_runs([runs["oracle-s0"], runs["oracle-short"]]))


def test_compare_finds_the_edge_loss_and_nothing_else(runs: dict[str, Path]) -> None:
    oracle = load_runs([runs["oracle-s0"], runs["oracle-s1"]])
    drop = load_runs([runs["drop-s0"], runs["drop-s1"]])

    comparison = compare_conditions(oracle, drop)

    rows = {row.metric: row for row in comparison.metrics}
    assert comparison.samples == 12
    edge = rows["edge_f1"].test
    assert edge.n == 12 and edge.mean_a == 1.0 and edge.mean_diff < 0 and edge.ci_high < 0
    assert max(edge.p_bootstrap, edge.p_ttest, edge.p_wilcoxon) < 0.01
    node = rows["node_f1"].test
    assert node.mean_diff == 0.0 and node.p_bootstrap == 1.0
    assert rows["node_f1"].p_holm == 1.0
    assert rows["edge_f1"].p_holm >= rows["edge_f1"].test.p_bootstrap


def test_compare_refuses_different_samples(runs: dict[str, Path]) -> None:
    with pytest.raises(IncompatibleRuns):
        compare_conditions(load_runs([runs["oracle-s0"]]), load_runs([runs["oracle-short"]]))


def test_cli_seeds_and_compare_write_markdown_and_json(
    runs: dict[str, Path], tmp_path: Path
) -> None:
    seeds_out = tmp_path / "seeds.md"
    compare_out = tmp_path / "compare.md"

    assert cli(["seeds", str(runs["drop-s0"]), str(runs["drop-s1"]), "--out", str(seeds_out)]) == 0
    assert (
        cli(
            [
                "compare",
                "--a",
                str(runs["oracle-s0"]),
                "--b",
                str(runs["drop-s0"]),
                "--metrics",
                "edge_f1",
                "graph_similarity",
                "--out",
                str(compare_out),
            ]
        )
        == 0
    )

    assert "seeds [0, 1]" in seeds_out.read_text()
    assert json.loads(seeds_out.with_suffix(".json").read_text())["samples"] == 12
    text = compare_out.read_text()
    assert "| edge_f1 | 12 | 1.000 |" in text and "graph_similarity" in text
    assert [
        m["metric"] for m in json.loads(compare_out.with_suffix(".json").read_text())["metrics"]
    ] == [
        "edge_f1",
        "graph_similarity",
    ]
