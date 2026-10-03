"""evaluation/scripts/runaway_report.py on the committed Phase 7 runs (no dataset needed)."""

from pathlib import Path

import pytest

from app.vlm.runaway import RunawayGuard
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
        # resolution ablation, all on the RTX 4080 SUPER (the -s0 run above is the A6000's)
        (
            "qwen3vl-2b-qlora-a6000-v1-px640-s0",
            {"truncated": 20, "failed": 20, "stuck_in_nodes": 19, "excess_edges": 1},
        ),
        (
            "qwen3vl-2b-qlora-a6000-v1-px768-s0",
            {"truncated": 14, "failed": 12, "stuck_in_nodes": 12, "excess_edges": 1, "other": 1},
        ),
        (
            "qwen3vl-2b-qlora-a6000-v1-px896-s0",
            {"truncated": 10, "failed": 9, "stuck_in_nodes": 9, "excess_edges": 1},
        ),
        (  # runaway guard on: stopped attempts count as truncated
            "qwen3vl-2b-qlora-a6000-v1-px896-guard-s0",
            {"truncated": 10, "failed": 10, "stuck_in_nodes": 9, "other": 1},
        ),
        (
            "qwen3vl-2b-qlora-a6000-v1-px1024-s0",
            {"truncated": 13, "failed": 12, "stuck_in_nodes": 10, "excess_edges": 1, "other": 2},
        ),
    ],
)
def test_l4_runaways_in_the_committed_runs(run_name: str, expected: dict[str, int]) -> None:
    run_dir = REPORTS / run_name

    table = runaway_by_level(read_results(run_dir), ground_truth(read_run(run_dir)))

    assert dict(table[4]) == {"samples": 28, **expected}


def test_the_guard_run_only_stopped_early() -> None:
    """Greedy decoding on one GPU: where the guard never fired, every attempt is byte-identical
    to the unguarded run; where it fired, the stopped text is a prefix of the unguarded text and
    the logged rule fires again on it."""
    guarded = {
        r.sample_id: r for r in read_results(REPORTS / "qwen3vl-2b-qlora-a6000-v1-px896-guard-s0")
    }
    plain = {r.sample_id: r for r in read_results(REPORTS / "qwen3vl-2b-qlora-a6000-v1-px896-s0")}
    stopped = 0
    for sample_id, result in guarded.items():
        attempts = result.prediction.analysis.extraction.attempts
        reference = plain[sample_id].prediction.analysis.extraction.attempts
        if all(a.output.finish_reason != "runaway" for a in attempts):
            assert [a.output.text for a in attempts] == [a.output.text for a in reference]
            continue
        stopped += 1
        first, unguarded = attempts[0].output, reference[0].output
        assert first.finish_reason == "runaway" and unguarded.finish_reason == "length"
        assert unguarded.text.startswith(first.text)
        for attempt in attempts:
            if attempt.output.finish_reason == "runaway":
                rule = RunawayGuard().check(attempt.output.text)
                assert rule.split(":")[0] == attempt.output.runaway.split(":")[0]

    assert stopped == 15
