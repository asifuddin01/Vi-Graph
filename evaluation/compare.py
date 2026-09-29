"""Across runs: variance over seeds (§20.10) and paired comparisons (§20.11).

- ``seed_summary``: runs of one condition that differ only in their seed → each metric as
  mean ± std of the per-run means (overall and per difficulty level, the §21 plot).
- ``compare_conditions``: condition A vs condition B, each one run or several seeds. Per
  sample, a condition's value is the mean over its runs; the paired tests (``stats``) then
  compare those per-sample values.

All runs involved must be on the same split build (split hash) and the same samples.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from evaluation.aggregate import SAMPLE_METRICS, macro
from evaluation.report import fmt
from evaluation.results import RunInfo, SampleResult, read_results, read_run
from evaluation.stats import PairedTest, holm, mean_std, paired_test

DEFAULT_METRICS = (
    "node_f1",
    "edge_f1",
    "edge_strict_f1",
    "graph_similarity",
    "label_accuracy",
    "qa_accuracy",
    "diagram_type_accuracy",
    "valid_first_attempt",
    "valid_post_repair",
)


class Run(BaseModel):
    path: str
    info: RunInfo
    results: list[SampleResult]


class IncompatibleRuns(ValueError):
    pass


def load_runs(paths: list[Path]) -> list[Run]:
    return [Run(path=str(p), info=read_run(p), results=read_results(p)) for p in paths]


def check_same_samples(runs: list[Run]) -> list[str]:
    hashes = {r.info.split.split_hash for r in runs}
    if len(hashes) > 1:
        raise IncompatibleRuns("runs use different split builds (split hashes differ)")
    ids = [[x.sample_id for x in r.results] for r in runs]
    if any(set(i) != set(ids[0]) for i in ids):
        raise IncompatibleRuns("runs cover different samples (different --limit or unfinished)")
    return ids[0]


class SeedSummary(BaseModel):
    runs: list[str]
    seeds: list[int]
    samples: int
    metrics: dict[str, dict[str, float | None]]  # metric → {mean, std} across runs
    by_level: dict[str, dict[str, dict[str, float | None]]]  # level → metric → {mean, std}


def seed_summary(runs: list[Run], metrics: tuple[str, ...] = DEFAULT_METRICS) -> SeedSummary:
    check_same_samples(runs)
    configs = [r.info.config.model_dump(exclude={"seed"}) for r in runs]
    if any(c != configs[0] for c in configs):
        differing = sorted(k for k in configs[0] if any(c[k] != configs[0][k] for c in configs))
        raise IncompatibleRuns(f"runs differ in more than the seed: {differing}")

    def across(results_per_run: list[list[SampleResult]], metric: str) -> dict[str, float | None]:
        values = [m for rs in results_per_run if (m := macro(rs, metric)["mean"]) is not None]
        mean, std = mean_std(values)
        return {"mean": mean, "std": std}

    levels = sorted(
        {str(x.attributes["level"]) for x in runs[0].results if "level" in x.attributes}
    )
    return SeedSummary(
        runs=[r.path for r in runs],
        seeds=[r.info.config.seed for r in runs],
        samples=len(runs[0].results),
        metrics={m: across([r.results for r in runs], m) for m in metrics},
        by_level={
            level: {
                m: across(
                    [
                        [x for x in r.results if str(x.attributes.get("level")) == level]
                        for r in runs
                    ],
                    m,
                )
                for m in metrics
            }
            for level in levels
        },
    )


class MetricComparison(BaseModel):
    metric: str
    test: PairedTest | None  # None when no sample has the metric under both conditions
    p_holm: float | None = None


class Comparison(BaseModel):
    a: list[str]
    b: list[str]
    samples: int
    metrics: list[MetricComparison]


def compare_conditions(
    a: list[Run], b: list[Run], metrics: tuple[str, ...] = DEFAULT_METRICS
) -> Comparison:
    ids = check_same_samples(a + b)
    rows = []
    for metric in metrics:
        pa, pb = _per_sample(a, metric), _per_sample(b, metric)
        both = [i for i in ids if pa.get(i) is not None and pb.get(i) is not None]
        test = paired_test([pa[i] for i in both], [pb[i] for i in both]) if both else None
        rows.append(MetricComparison(metric=metric, test=test))
    tested = [r for r in rows if r.test is not None]
    for row, adjusted in zip(tested, holm([r.test.p_bootstrap for r in tested]), strict=True):
        row.p_holm = adjusted
    return Comparison(a=[r.path for r in a], b=[r.path for r in b], samples=len(ids), metrics=rows)


def _per_sample(runs: list[Run], metric: str) -> dict[str, float | None]:
    """Per sample: the mean over this condition's runs (None if undefined in any run)."""
    values: dict[str, list[float | None]] = {}
    for run in runs:
        for result in run.results:
            values.setdefault(result.sample_id, []).append(SAMPLE_METRICS[metric](result))
    return {
        sample: None if any(v is None for v in vs) else sum(vs) / len(vs)
        for sample, vs in values.items()
    }


def render_seeds(summary: SeedSummary) -> str:
    lines = [
        f"# Run-to-run variance: {len(summary.runs)} runs (seeds {summary.seeds}), "
        f"{summary.samples} samples each",
        "",
        "Mean ± std of the per-run means.",
        "",
        "| Metric | Mean | Std |",
        "| --- | --- | --- |",
    ]
    for metric, row in summary.metrics.items():
        lines.append(f"| {metric} | {fmt(row['mean'])} | {fmt(row['std'])} |")
    if summary.by_level:
        shown = [
            m
            for m in ("node_f1", "edge_f1", "graph_similarity", "qa_accuracy")
            if m in summary.metrics
        ]
        lines += [
            "",
            "## By level",
            "",
            "| Level | " + " | ".join(shown) + " |",
            "| --- | " + " | ".join("---" for _ in shown) + " |",
        ]
        for level, row in summary.by_level.items():
            cells = " | ".join(f"{fmt(row[m]['mean'])} ± {fmt(row[m]['std'])}" for m in shown)
            lines.append(f"| {level} | {cells} |")
    return "\n".join(lines) + "\n"


def render_comparison(comparison: Comparison) -> str:
    lines = [
        "# Paired comparison",
        "",
        f"- A: {', '.join(f'`{p}`' for p in comparison.a)}",
        f"- B: {', '.join(f'`{p}`' for p in comparison.b)}",
        f"- {comparison.samples} paired samples. Δ = B − A. Primary test: paired bootstrap "
        "(10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test "
        "and Wilcoxon signed-rank for reference.",
        "",
        "| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in comparison.metrics:
        t = row.test
        if t is None:
            lines.append(f"| {row.metric} | 0 | – | – | – | – | – | – | – | – |")
            continue
        lines.append(
            f"| {row.metric} | {t.n} | {fmt(t.mean_a)} | {fmt(t.mean_b)} | {t.mean_diff:+.3f} "
            f"| [{t.ci_low:+.3f}, {t.ci_high:+.3f}] | {fmt(t.p_bootstrap, 4)} "
            f"| {fmt(row.p_holm, 4)} | {fmt(t.p_ttest, 4)} | {fmt(t.p_wilcoxon, 4)} |"
        )
    return "\n".join(lines) + "\n"
