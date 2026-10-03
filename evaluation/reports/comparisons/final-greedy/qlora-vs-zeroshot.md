# Paired comparison

- A: `E:\Asif\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-final-greedy`
- B: `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-final-greedy`
- 500 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 500 | 0.703 | 0.854 | +0.151 | [+0.122, +0.183] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| edge_f1 | 500 | 0.499 | 0.638 | +0.139 | [+0.114, +0.164] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| edge_strict_f1 | 500 | 0.415 | 0.611 | +0.196 | [+0.172, +0.220] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| graph_similarity | 500 | 0.581 | 0.740 | +0.159 | [+0.137, +0.181] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| label_accuracy | 357 | 0.980 | 0.997 | +0.017 | [+0.012, +0.023] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| qa_accuracy | 500 | 0.437 | 0.582 | +0.145 | [+0.123, +0.168] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| diagram_type_accuracy | 500 | 0.334 | 0.882 | +0.548 | [+0.504, +0.592] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| valid_first_attempt | 500 | 0.512 | 0.728 | +0.216 | [+0.168, +0.264] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| valid_post_repair | 500 | 0.720 | 0.910 | +0.190 | [+0.154, +0.226] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
