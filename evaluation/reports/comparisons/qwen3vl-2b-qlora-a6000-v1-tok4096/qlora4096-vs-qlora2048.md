# Paired comparison

- A: `F:\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-s0`
- B: `F:\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-tok4096-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.844 | 0.844 | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| edge_f1 | 112 | 0.624 | 0.624 | -0.000 | [-0.001, +0.000] | 0.6293 | 1.0000 | 0.3195 | 0.3173 |
| edge_strict_f1 | 112 | 0.591 | 0.591 | -0.000 | [-0.001, +0.000] | 0.6293 | 1.0000 | 0.3195 | 0.3173 |
| graph_similarity | 112 | 0.727 | 0.727 | -0.000 | [-0.000, +0.000] | 0.6293 | 1.0000 | 0.3195 | 0.3173 |
| label_accuracy | 100 | 0.985 | 0.985 | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| qa_accuracy | 112 | 0.564 | 0.562 | -0.002 | [-0.005, +0.000] | 0.6293 | 1.0000 | 0.3195 | 0.3173 |
| diagram_type_accuracy | 112 | 0.866 | 0.866 | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_first_attempt | 112 | 0.670 | 0.670 | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| valid_post_repair | 112 | 0.893 | 0.893 | +0.000 | [+0.000, +0.000] | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
