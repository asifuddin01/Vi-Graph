import numpy as np
import pytest

from evaluation.stats import holm, mean_std, paired_test


def test_identical_conditions_show_no_difference() -> None:
    a = [0.2, 0.5, 0.9, 0.4, 0.7]

    result = paired_test(a, list(a))

    assert result.mean_diff == 0.0
    assert (result.ci_low, result.ci_high) == (0.0, 0.0)
    assert result.p_bootstrap == 1.0 and result.p_ttest == 1.0 and result.p_wilcoxon == 1.0


def test_a_clear_improvement_is_significant() -> None:
    rng = np.random.default_rng(1)
    a = rng.uniform(0.3, 0.7, 200)
    b = a + 0.2 + rng.normal(0, 0.05, 200)

    result = paired_test(list(a), list(b))

    assert result.mean_diff == pytest.approx(0.2, abs=0.02)
    assert result.ci_low > 0.15 and result.ci_high < 0.25
    assert result.p_bootstrap < 0.001 and result.p_ttest < 1e-10 and result.p_wilcoxon < 1e-10
    assert result.n == 200 and result.mean_b > result.mean_a


def test_noise_alone_is_not_significant() -> None:
    rng = np.random.default_rng(2)
    a = rng.uniform(0, 1, 300)
    b = a + rng.normal(0, 0.1, 300)

    result = paired_test(list(a), list(b))

    assert result.ci_low < 0 < result.ci_high
    assert result.p_bootstrap > 0.05 and result.p_ttest > 0.05


def test_bootstrap_and_t_test_agree_on_normal_differences() -> None:
    rng = np.random.default_rng(3)
    a = rng.uniform(0, 1, 400)
    b = a + rng.normal(0.01, 0.1, 400)

    result = paired_test(list(a), list(b))

    assert result.p_bootstrap == pytest.approx(result.p_ttest, abs=0.03)


def test_bootstrap_is_deterministic_per_seed() -> None:
    a, b = [0.1, 0.4, 0.3, 0.9], [0.2, 0.3, 0.6, 0.8]

    assert paired_test(a, b, seed=5) == paired_test(a, b, seed=5)


def test_paired_test_needs_equal_non_empty_lists() -> None:
    with pytest.raises(ValueError):
        paired_test([0.1], [0.1, 0.2])
    with pytest.raises(ValueError):
        paired_test([], [])


def test_holm_adjusts_in_input_order() -> None:
    assert holm([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert holm([0.5, 0.9]) == pytest.approx([1.0, 1.0])
    assert holm([]) == []


def test_mean_std() -> None:
    assert mean_std([]) == (None, None)
    assert mean_std([0.5]) == (0.5, None)
    mean, std = mean_std([0.2, 0.4])
    assert mean == pytest.approx(0.3) and std == pytest.approx(0.1414, abs=1e-4)
