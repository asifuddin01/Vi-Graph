# Paired comparison

- A: `evaluation/reports/qwen3vl-2b-qlora-a6000-v1-px640-s0`
- B: `evaluation/reports/qwen3vl-2b-qlora-a6000-v1-px768-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.784 | 0.823 | +0.039 | [-0.007, +0.086] | 0.0984 | 0.3936 | 0.1013 | 0.0134 |
| edge_f1 | 112 | 0.581 | 0.626 | +0.046 | [+0.016, +0.080] | 0.0069 | 0.0552 | 0.0059 | 0.0116 |
| edge_strict_f1 | 112 | 0.556 | 0.608 | +0.051 | [+0.020, +0.086] | 0.0035 | 0.0315 | 0.0030 | 0.0059 |
| graph_similarity | 112 | 0.677 | 0.720 | +0.043 | [+0.010, +0.077] | 0.0105 | 0.0735 | 0.0118 | 0.0022 |
| label_accuracy | 88 | 0.989 | 0.993 | +0.004 | [-0.002, +0.011] | 0.2316 | 0.4632 | 0.2435 | 0.2318 |
| qa_accuracy | 112 | 0.538 | 0.572 | +0.034 | [+0.001, +0.070] | 0.0503 | 0.3018 | 0.0540 | 0.0994 |
| diagram_type_accuracy | 112 | 0.804 | 0.857 | +0.054 | [-0.009, +0.116] | 0.1049 | 0.3936 | 0.0833 | 0.0833 |
| valid_first_attempt | 112 | 0.714 | 0.688 | -0.027 | [-0.107, +0.054] | 0.5858 | 0.5858 | 0.5151 | 0.5127 |
| valid_post_repair | 112 | 0.812 | 0.875 | +0.062 | [+0.000, +0.125] | 0.0689 | 0.3445 | 0.0518 | 0.0522 |
