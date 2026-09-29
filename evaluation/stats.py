"""Statistics for comparing runs (spec §20.10–20.11).

Primary test: **paired bootstrap** over test samples. For per-sample differences d = b − a
(one value per sample, both conditions scored on the same samples), resample the samples
with replacement ``RESAMPLES`` times; the 95% confidence interval of the mean difference is
the 2.5th–97.5th percentile of the resampled means, and the two-sided p-value is the share
of resampled means at least as far from the observed mean as the observed mean is from 0
(the bootstrap distribution shifted to the null), with a +1 correction. The paired t-test
and the Wilcoxon signed-rank test are reported alongside. When several metrics are
compared at once, Holm–Bonferroni adjusted p-values control the family-wise error rate.
"""

from __future__ import annotations

import math
import statistics

import numpy as np
from pydantic import BaseModel
from scipy import stats

RESAMPLES = 10_000
CONFIDENCE = 0.95


class PairedTest(BaseModel):
    n: int
    mean_a: float
    mean_b: float
    mean_diff: float  # b − a
    ci_low: float
    ci_high: float
    p_bootstrap: float
    p_ttest: float | None
    p_wilcoxon: float | None


def paired_test(
    a: list[float], b: list[float], *, resamples: int = RESAMPLES, seed: int = 0
) -> PairedTest:
    if len(a) != len(b) or not a:
        raise ValueError("paired tests need two equally long, non-empty lists")
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    diffs = y - x
    observed = float(diffs.mean())
    rng = np.random.default_rng(seed)
    means = diffs[rng.integers(0, len(diffs), size=(resamples, len(diffs)))].mean(axis=1)
    tail = (1 - CONFIDENCE) / 2
    extreme = np.count_nonzero(np.abs(means - observed) >= abs(observed) - 1e-12)
    return PairedTest(
        n=len(diffs),
        mean_a=float(x.mean()),
        mean_b=float(y.mean()),
        mean_diff=observed,
        ci_low=float(np.quantile(means, tail)),
        ci_high=float(np.quantile(means, 1 - tail)),
        p_bootstrap=min(1.0, (extreme + 1) / (resamples + 1)),
        p_ttest=_ttest(diffs),
        p_wilcoxon=_wilcoxon(diffs),
    )


def _ttest(diffs: np.ndarray) -> float | None:
    if len(diffs) < 2:
        return None
    if np.allclose(diffs, diffs[0]):
        return 1.0 if math.isclose(float(diffs[0]), 0.0, abs_tol=1e-12) else 0.0
    return float(stats.ttest_1samp(diffs, 0.0).pvalue)


def _wilcoxon(diffs: np.ndarray) -> float | None:
    nonzero = diffs[np.abs(diffs) > 1e-12]
    if len(nonzero) == 0:
        return 1.0
    if len(diffs) < 2:
        return None
    return float(stats.wilcoxon(diffs, zero_method="wilcox").pvalue)


def holm(p_values: list[float]) -> list[float]:
    """Holm–Bonferroni adjusted p-values, in the input order."""
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [0.0] * len(p_values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def mean_std(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return statistics.fmean(values), statistics.stdev(values) if len(values) > 1 else None
