# Paired comparison

- A: `evaluation/reports/qwen3vl-2b-qlora-a6000-v1-s0`
- B: `evaluation/reports/qwen3vl-2b-qlora-a6000-v1-px896-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.844 | 0.846 | +0.002 | [-0.027, +0.030] | 0.9120 | 1.0000 | 0.9106 | 0.8076 |
| edge_f1 | 112 | 0.624 | 0.633 | +0.009 | [-0.016, +0.034] | 0.4846 | 1.0000 | 0.4952 | 0.7005 |
| edge_strict_f1 | 112 | 0.591 | 0.595 | +0.004 | [-0.020, +0.029] | 0.7570 | 1.0000 | 0.7631 | 0.8904 |
| graph_similarity | 112 | 0.727 | 0.730 | +0.004 | [-0.020, +0.027] | 0.7491 | 1.0000 | 0.7594 | 0.7588 |
| label_accuracy | 98 | 0.989 | 0.991 | +0.002 | [-0.001, +0.007] | 0.2505 | 1.0000 | 0.2694 | 0.3452 |
| qa_accuracy | 112 | 0.564 | 0.573 | +0.009 | [-0.010, +0.028] | 0.3589 | 1.0000 | 0.3637 | 0.4165 |
| diagram_type_accuracy | 112 | 0.866 | 0.857 | -0.009 | [-0.045, +0.018] | 0.7589 | 1.0000 | 0.5660 | 0.5637 |
| valid_first_attempt | 112 | 0.670 | 0.661 | -0.009 | [-0.071, +0.054] | 0.8779 | 1.0000 | 0.7645 | 0.7630 |
| valid_post_repair | 112 | 0.893 | 0.893 | +0.000 | [-0.036, +0.036] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
