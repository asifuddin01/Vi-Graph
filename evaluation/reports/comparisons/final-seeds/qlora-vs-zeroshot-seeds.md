# Paired comparison

- A: `E:\Asif\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-final-t0.7-s0`, `E:\Asif\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-final-t0.7-s1`, `E:\Asif\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-final-t0.7-s2`
- B: `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-final-t0.7-s0`, `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-final-t0.7-s1`, `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-final-t0.7-s2`
- 500 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 500 | 0.708 | 0.869 | +0.160 | [+0.135, +0.187] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| edge_f1 | 500 | 0.495 | 0.639 | +0.144 | [+0.122, +0.165] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| edge_strict_f1 | 500 | 0.411 | 0.614 | +0.203 | [+0.182, +0.224] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| graph_similarity | 500 | 0.582 | 0.748 | +0.167 | [+0.148, +0.185] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| label_accuracy | 326 | 0.983 | 0.996 | +0.013 | [+0.009, +0.017] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| qa_accuracy | 500 | 0.441 | 0.581 | +0.140 | [+0.122, +0.158] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| diagram_type_accuracy | 500 | 0.342 | 0.909 | +0.567 | [+0.527, +0.607] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| valid_first_attempt | 500 | 0.507 | 0.718 | +0.211 | [+0.169, +0.253] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| valid_post_repair | 500 | 0.727 | 0.937 | +0.210 | [+0.178, +0.243] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
