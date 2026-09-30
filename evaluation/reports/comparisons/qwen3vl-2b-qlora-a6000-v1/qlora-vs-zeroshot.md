# Paired comparison

- A: `F:\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-s0`
- B: `F:\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.712 | 0.844 | +0.132 | [+0.066, +0.200] | 0.0001 | 0.0009 | 0.0002 | 0.0016 |
| edge_f1 | 112 | 0.497 | 0.624 | +0.127 | [+0.082, +0.178] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| edge_strict_f1 | 112 | 0.420 | 0.591 | +0.171 | [+0.126, +0.218] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| graph_similarity | 112 | 0.586 | 0.727 | +0.140 | [+0.095, +0.187] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| label_accuracy | 79 | 0.985 | 0.999 | +0.014 | [+0.005, +0.026] | 0.0145 | 0.0192 | 0.0118 | 0.0033 |
| qa_accuracy | 112 | 0.451 | 0.564 | +0.113 | [+0.064, +0.162] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| diagram_type_accuracy | 112 | 0.321 | 0.866 | +0.545 | [+0.446, +0.643] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| valid_first_attempt | 112 | 0.509 | 0.670 | +0.161 | [+0.045, +0.277] | 0.0096 | 0.0192 | 0.0088 | 0.0094 |
| valid_post_repair | 112 | 0.723 | 0.893 | +0.170 | [+0.089, +0.250] | 0.0001 | 0.0009 | 0.0000 | 0.0001 |
