# Paired comparison

- A: `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-px896-s0`
- B: `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-px896-guard-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.846 | 0.853 | +0.008 | [-0.017, +0.036] | 0.5876 | 1.0000 | 0.5745 | 0.4652 |
| edge_f1 | 112 | 0.633 | 0.637 | +0.005 | [-0.008, +0.022] | 0.5349 | 1.0000 | 0.5465 | 0.6858 |
| edge_strict_f1 | 112 | 0.595 | 0.600 | +0.005 | [-0.007, +0.021] | 0.5037 | 1.0000 | 0.5097 | 0.6858 |
| graph_similarity | 112 | 0.730 | 0.736 | +0.006 | [-0.012, +0.028] | 0.5888 | 1.0000 | 0.5834 | 0.8927 |
| label_accuracy | 99 | 0.990 | 0.990 | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| qa_accuracy | 112 | 0.573 | 0.570 | -0.003 | [-0.018, +0.011] | 0.6849 | 1.0000 | 0.6977 | 0.6858 |
| diagram_type_accuracy | 112 | 0.857 | 0.866 | +0.009 | [-0.018, +0.045] | 0.7564 | 1.0000 | 0.5660 | 0.5637 |
| valid_first_attempt | 112 | 0.661 | 0.661 | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_post_repair | 112 | 0.893 | 0.902 | +0.009 | [-0.018, +0.045] | 0.7564 | 1.0000 | 0.5660 | 0.5637 |
