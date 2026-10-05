"""The final evaluation's published numbers (README, research/paper/report.md) come from these
committed runs, and the three systems are paired: same split build, same 500 samples."""

import json
from pathlib import Path

import pytest

from evaluation.results import read_results, read_run

REPORTS = Path(__file__).resolve().parents[1] / "reports"
FINAL = {
    "baseline": "baseline-v1-final",
    "zeroshot": "qwen3-vl-2b-instruct-zeroshot-final-greedy",
    "qlora": "qwen3vl-2b-qlora-a6000-v1-final-greedy",
}


def macro(run: str, metric: str) -> float:
    summary = json.loads((REPORTS / run / "summary.json").read_text())
    return round(summary["macro"][metric]["mean"], 3)


def test_the_final_runs_are_paired() -> None:
    runs = [read_run(REPORTS / name) for name in FINAL.values()]
    ids = [[r.sample_id for r in read_results(REPORTS / name)] for name in FINAL.values()]

    assert {r.split.split_hash for r in runs} == {
        "88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3"
    }
    assert all(len(i) == 500 for i in ids) and ids[0] == ids[1] == ids[2]
    assert all(r.samples_done == 500 and r.errors == 0 for r in runs)


@pytest.mark.parametrize(
    ("system", "graph_similarity", "edge_f1", "qa_accuracy", "valid"),
    [
        ("baseline", 0.738, 0.610, 0.450, 0.998),
        ("zeroshot", 0.581, 0.499, 0.437, 0.720),
        ("qlora", 0.740, 0.638, 0.582, 0.910),
    ],
)
def test_headline_numbers(
    system: str, graph_similarity: float, edge_f1: float, qa_accuracy: float, valid: float
) -> None:
    run = FINAL[system]

    assert macro(run, "graph_similarity") == graph_similarity
    assert macro(run, "edge_f1") == edge_f1
    assert macro(run, "qa_accuracy") == qa_accuracy
    assert macro(run, "valid_post_repair") == valid


def test_vlm_runs_used_the_final_protocol() -> None:
    for name in (FINAL["zeroshot"], FINAL["qlora"]):
        config = read_run(REPORTS / name).config
        assert (config.image_max_side, config.max_new_tokens) == (896, 2048)
        assert config.temperature == 0.0 and config.runaway_guard == "1"
