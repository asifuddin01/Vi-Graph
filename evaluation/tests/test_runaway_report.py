"""evaluation/scripts/runaway_report.py on the committed Phase 7 runs (no dataset needed)."""

from pathlib import Path

import pytest

from evaluation.results import read_results, read_run
from evaluation.scripts.runaway_report import classify, ground_truth, runaway_by_level
from evaluation.tests.helpers import graph

REPORTS = Path(__file__).resolve().parents[1] / "reports"
TWO_EDGES = graph([("n1", "A"), ("n2", "B"), ("n3", "C")], [("n1", "n2"), ("n2", "n3")])


def edges(*pairs: tuple[str, str]) -> str:
    return ", ".join(f'{{"source": "{s}", "target": "{t}"}}' for s, t in pairs)


def test_classify() -> None:
    assert classify('{"nodes": [{"id": "n1"}, {"id": "n2"}, {"id": "n3"', TWO_EDGES) == (
        "stuck_in_nodes"
    )
    assert classify(f'"edges": [{edges(*[("n1", "n2")] * 4)}', TWO_EDGES) == "repeating_edges"
    many = [("n1", f"n{i}") for i in range(2, 7)]
    assert classify(f'"edges": [{edges(*many)}', TWO_EDGES) == "excess_edges"
    assert classify(f'"edges": [{edges(("n1", "n2"), ("n2", "n3"))}', TWO_EDGES) == "other"


def test_ground_truth_reproduces_the_runs_split() -> None:
    run = read_run(REPORTS / "qwen3vl-2b-qlora-a6000-v1-tok4096-s0")

    graphs = ground_truth(run)

    assert len(graphs) == 500 and "test-000111" in graphs
    tampered = run.model_copy(update={"split": run.split.model_copy(update={"graph_hash": "0"})})
    with pytest.raises(SystemExit, match="does not match"):
        ground_truth(tampered)


@pytest.mark.parametrize(
    ("run_name", "expected"),
    [
        (
            "qwen3-vl-2b-instruct-zeroshot-s0",
            {"truncated": 27, "failed": 27, "stuck_in_nodes": 19, "other": 8},
        ),
        (
            "qwen3-vl-2b-instruct-zeroshot-tok4096-s0",
            {
                "truncated": 22,
                "failed": 22,
                "stuck_in_nodes": 19,
                "repeating_edges": 2,
                "excess_edges": 1,
            },
        ),
        (
            "qwen3vl-2b-qlora-a6000-v1-s0",
            {"truncated": 11, "failed": 10, "stuck_in_nodes": 9, "excess_edges": 2},
        ),
        (
            "qwen3vl-2b-qlora-a6000-v1-tok4096-s0",
            {"truncated": 11, "failed": 10, "stuck_in_nodes": 9, "excess_edges": 2},
        ),
    ],
)
def test_l4_runaways_in_the_committed_runs(run_name: str, expected: dict[str, int]) -> None:
    run_dir = REPORTS / run_name

    table = runaway_by_level(read_results(run_dir), ground_truth(read_run(run_dir)))

    assert dict(table[4]) == {"samples": 28, **expected}
