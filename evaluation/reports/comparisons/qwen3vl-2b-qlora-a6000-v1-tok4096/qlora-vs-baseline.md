# Paired comparison

- A: `F:\vigraph\output\eval\baseline-v1-windows`
- B: `F:\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-tok4096-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.865 | 0.844 | -0.021 | [-0.072, +0.025] | 0.4022 | 1.0000 | 0.4056 | 0.1667 |
| edge_f1 | 112 | 0.620 | 0.624 | +0.003 | [-0.051, +0.057] | 0.9053 | 1.0000 | 0.9073 | 0.9687 |
| edge_strict_f1 | 112 | 0.569 | 0.591 | +0.022 | [-0.035, +0.079] | 0.4367 | 1.0000 | 0.4440 | 0.4660 |
| graph_similarity | 112 | 0.736 | 0.727 | -0.009 | [-0.055, +0.034] | 0.6807 | 1.0000 | 0.6795 | 0.3779 |
| label_accuracy | 99 | 0.906 | 0.986 | +0.080 | [+0.054, +0.110] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| qa_accuracy | 112 | 0.447 | 0.562 | +0.115 | [+0.064, +0.170] | 0.0001 | 0.0008 | 0.0001 | 0.0002 |
| diagram_type_accuracy | 112 | 0.732 | 0.866 | +0.134 | [+0.036, +0.232] | 0.0097 | 0.0485 | 0.0084 | 0.0090 |
| valid_first_attempt | 0 | – | – | – | – | – | – | – | – |
| valid_post_repair | 112 | 1.000 | 0.893 | -0.107 | [-0.170, -0.054] | 0.0005 | 0.0030 | 0.0004 | 0.0005 |
