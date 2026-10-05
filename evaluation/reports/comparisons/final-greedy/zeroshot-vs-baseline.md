# Paired comparison

- A: `/home/user/Vi-Graph/evaluation/reports/baseline-v1-final`
- B: `/home/user/Vi-Graph/evaluation/reports/qwen3-vl-2b-instruct-zeroshot-final-greedy`
- 500 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 500 | 0.872 | 0.703 | -0.169 | [-0.202, -0.136] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| edge_f1 | 500 | 0.610 | 0.499 | -0.110 | [-0.141, -0.079] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| edge_strict_f1 | 500 | 0.562 | 0.415 | -0.147 | [-0.174, -0.120] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| graph_similarity | 500 | 0.738 | 0.581 | -0.157 | [-0.183, -0.130] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| label_accuracy | 360 | 0.947 | 0.979 | +0.032 | [+0.025, +0.041] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| qa_accuracy | 500 | 0.450 | 0.437 | -0.013 | [-0.039, +0.014] | 0.3292 | 0.3292 | 0.3270 | 0.1677 |
| diagram_type_accuracy | 500 | 0.702 | 0.334 | -0.368 | [-0.424, -0.310] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| valid_first_attempt | 0 | – | – | – | – | – | – | – | – |
| valid_post_repair | 500 | 0.998 | 0.720 | -0.278 | [-0.318, -0.238] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
