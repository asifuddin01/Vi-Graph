"""Raw VLM output vs the validated / retried / repaired / normalized output (§24D, H4).

    PYTHONPATH=backend:. python evaluation/scripts/repair_ablation.py RUN_DIR [...] [--out FILE.md]

Every evaluation run already stores both scores per sample: ``first_attempt_scores`` (attempt 1
exactly as the model wrote it: no retry, no repair, no normalization; unparseable or invalid
output scores as an empty graph) and ``scores`` (what the app returns after Stage C and D). So
the ablation needs no extra model calls: per run, a paired test of first attempt → final on
the same samples (paired bootstrap, Holm across the metrics, as in evaluation/stats.py), plus
where the final graphs came from (Stage C status).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from evaluation.metrics.scores import SampleScores
from evaluation.results import SampleResult, read_results, read_run
from evaluation.stats import PairedTest, holm, paired_test

METRICS: dict[str, Callable[[SampleScores], float]] = {
    "valid": lambda s: float(s.has_graph),
    "node_f1": lambda s: s.nodes.f1,
    "edge_f1": lambda s: s.edges.f1,
    "edge_strict_f1": lambda s: s.edges_strict.f1,
    "graph_similarity": lambda s: s.graph_similarity,
    "diagram_type_accuracy": lambda s: float(s.diagram_type_correct),
}
STATUSES = ("valid_first_attempt", "valid_after_retry", "repaired", "failed")


def ablation(results: list[SampleResult]) -> dict[str, tuple[PairedTest, float]]:
    """Per metric: the paired test (a = first attempt, b = final) and its Holm-adjusted p."""
    tests = {
        name: paired_test(
            [metric(r.first_attempt_scores) for r in results], [metric(r.scores) for r in results]
        )
        for name, metric in METRICS.items()
    }
    adjusted = holm([t.p_bootstrap for t in tests.values()])
    return {name: (test, p) for (name, test), p in zip(tests.items(), adjusted, strict=True)}


def sources(results: list[SampleResult]) -> dict[str, tuple[int, float]]:
    """Per Stage C status: (samples, mean final graph similarity)."""
    by_status: dict[str, list[float]] = {}
    for r in results:
        status = r.prediction.analysis.extraction.status if r.prediction.analysis else "failed"
        by_status.setdefault(status, []).append(r.scores.graph_similarity)
    return {s: (len(v), sum(v) / len(v)) for s in STATUSES if (v := by_status.get(s))}


def render(run_dir: Path) -> str:
    results = read_results(run_dir)
    lines = [
        f"## {read_run(run_dir).name} ({len(results)} samples)",
        "",
        "| Metric | First attempt (raw) | Final (Stage C + D) | Δ | 95% CI | p (Holm) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name, (t, p) in ablation(results).items():
        lines.append(
            f"| {name} | {t.mean_a:.3f} | {t.mean_b:.3f} | {t.mean_diff:+.3f} | "
            f"[{t.ci_low:+.3f}, {t.ci_high:+.3f}] | {p:.4f} |"
        )
    lines += ["", "| Final graph from | Samples | Mean graph similarity |", "| --- | --- | --- |"]
    lines += [f"| {s} | {n} | {mean:.3f} |" for s, (n, mean) in sources(results).items()]
    retried = Counter(
        len(r.prediction.analysis.extraction.attempts) for r in results if r.prediction.analysis
    )
    lines += ["", f"Attempts per sample: {dict(sorted(retried.items()))}", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="repair_ablation.py")
    parser.add_argument("run_dirs", type=Path, nargs="+")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    text = "# Repair ablation (§24D): first attempt as-is vs final output\n\n" + "\n".join(
        render(run_dir) for run_dir in args.run_dirs
    )
    print(text)
    if args.out:
        args.out.write_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
