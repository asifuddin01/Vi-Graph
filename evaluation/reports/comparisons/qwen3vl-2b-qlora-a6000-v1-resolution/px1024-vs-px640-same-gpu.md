# Paired comparison

- A: `evaluation/reports/qwen3vl-2b-qlora-a6000-v1-px640-s0`
- B: `evaluation/reports/qwen3vl-2b-qlora-a6000-v1-px1024-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.784 | 0.855 | +0.071 | [+0.017, +0.126] | 0.0117 | 0.0585 | 0.0133 | 0.0032 |
| edge_f1 | 112 | 0.581 | 0.659 | +0.078 | [+0.044, +0.116] | 0.0001 | 0.0009 | 0.0000 | 0.0001 |
| edge_strict_f1 | 112 | 0.556 | 0.627 | +0.071 | [+0.036, +0.108] | 0.0003 | 0.0024 | 0.0002 | 0.0003 |
| graph_similarity | 112 | 0.677 | 0.749 | +0.072 | [+0.032, +0.114] | 0.0011 | 0.0066 | 0.0009 | 0.0003 |
| label_accuracy | 88 | 0.989 | 0.997 | +0.008 | [+0.002, +0.015] | 0.0223 | 0.0892 | 0.0291 | 0.0293 |
| qa_accuracy | 112 | 0.538 | 0.590 | +0.052 | [+0.022, +0.083] | 0.0007 | 0.0049 | 0.0014 | 0.0042 |
| diagram_type_accuracy | 112 | 0.804 | 0.875 | +0.071 | [+0.000, +0.143] | 0.0553 | 0.1122 | 0.0450 | 0.0455 |
| valid_first_attempt | 112 | 0.714 | 0.670 | -0.045 | [-0.134, +0.045] | 0.3673 | 0.3673 | 0.3195 | 0.3173 |
| valid_post_repair | 112 | 0.812 | 0.884 | +0.071 | [+0.009, +0.134] | 0.0374 | 0.1122 | 0.0319 | 0.0325 |
