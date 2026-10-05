# Paired comparison

- A: `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-final-greedy`
- B: `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-final-t0.7-s0`, `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-final-t0.7-s1`, `E:\Asif\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-final-t0.7-s2`
- 500 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 500 | 0.854 | 0.869 | +0.014 | [+0.001, +0.029] | 0.0482 | 0.3374 | 0.0463 | 0.8653 |
| edge_f1 | 500 | 0.638 | 0.639 | +0.000 | [-0.010, +0.011] | 0.9355 | 1.0000 | 0.9356 | 0.6455 |
| edge_strict_f1 | 500 | 0.611 | 0.614 | +0.003 | [-0.007, +0.013] | 0.5717 | 1.0000 | 0.5674 | 0.9163 |
| graph_similarity | 500 | 0.740 | 0.748 | +0.008 | [-0.002, +0.019] | 0.1123 | 0.6737 | 0.1117 | 0.8217 |
| label_accuracy | 435 | 0.986 | 0.986 | -0.001 | [-0.004, +0.003] | 0.7561 | 1.0000 | 0.7513 | 0.0021 |
| qa_accuracy | 500 | 0.582 | 0.581 | -0.001 | [-0.013, +0.011] | 0.8386 | 1.0000 | 0.8429 | 0.5999 |
| diagram_type_accuracy | 500 | 0.882 | 0.909 | +0.027 | [+0.009, +0.045] | 0.0045 | 0.0405 | 0.0036 | 0.0185 |
| valid_first_attempt | 500 | 0.728 | 0.718 | -0.010 | [-0.040, +0.021] | 0.5301 | 1.0000 | 0.5172 | 0.0109 |
| valid_post_repair | 500 | 0.910 | 0.937 | +0.027 | [+0.009, +0.047] | 0.0046 | 0.0405 | 0.0043 | 0.0184 |
