# Paired comparison

- A: `E:\Asif\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-final-greedy`
- B: `E:\Asif\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-final-t0.7-s0`, `E:\Asif\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-final-t0.7-s1`, `E:\Asif\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-final-t0.7-s2`
- 500 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 500 | 0.703 | 0.708 | +0.005 | [-0.012, +0.023] | 0.5770 | 1.0000 | 0.5746 | 0.8777 |
| edge_f1 | 500 | 0.499 | 0.495 | -0.004 | [-0.016, +0.007] | 0.4263 | 1.0000 | 0.4322 | 0.1499 |
| edge_strict_f1 | 500 | 0.415 | 0.411 | -0.004 | [-0.014, +0.005] | 0.3889 | 1.0000 | 0.3833 | 0.3006 |
| graph_similarity | 500 | 0.581 | 0.582 | +0.000 | [-0.012, +0.013] | 0.9445 | 1.0000 | 0.9419 | 0.3437 |
| label_accuracy | 326 | 0.982 | 0.983 | +0.000 | [-0.001, +0.003] | 0.7069 | 1.0000 | 0.7034 | 0.5702 |
| qa_accuracy | 500 | 0.437 | 0.441 | +0.004 | [-0.006, +0.014] | 0.4423 | 1.0000 | 0.4438 | 0.7821 |
| diagram_type_accuracy | 500 | 0.334 | 0.342 | +0.008 | [-0.009, +0.025] | 0.3962 | 1.0000 | 0.3716 | 0.6982 |
| valid_first_attempt | 500 | 0.512 | 0.507 | -0.005 | [-0.026, +0.015] | 0.6418 | 1.0000 | 0.6134 | 0.0394 |
| valid_post_repair | 500 | 0.720 | 0.727 | +0.007 | [-0.012, +0.027] | 0.4898 | 1.0000 | 0.4639 | 0.4175 |
