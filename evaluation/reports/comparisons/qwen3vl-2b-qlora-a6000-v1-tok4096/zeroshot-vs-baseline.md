# Paired comparison

- A: `F:\vigraph\output\eval\baseline-v1-windows`
- B: `F:\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-tok4096-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.865 | 0.736 | -0.129 | [-0.195, -0.068] | 0.0002 | 0.0008 | 0.0001 | 0.0160 |
| edge_f1 | 112 | 0.620 | 0.502 | -0.118 | [-0.175, -0.063] | 0.0001 | 0.0008 | 0.0001 | 0.0001 |
| edge_strict_f1 | 112 | 0.569 | 0.432 | -0.136 | [-0.189, -0.086] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| graph_similarity | 112 | 0.736 | 0.601 | -0.135 | [-0.186, -0.086] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| label_accuracy | 85 | 0.939 | 0.971 | +0.032 | [+0.017, +0.050] | 0.0003 | 0.0008 | 0.0002 | 0.0001 |
| qa_accuracy | 112 | 0.447 | 0.454 | +0.007 | [-0.039, +0.053] | 0.7662 | 0.7662 | 0.7649 | 0.9794 |
| diagram_type_accuracy | 112 | 0.732 | 0.339 | -0.393 | [-0.509, -0.268] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| valid_first_attempt | 0 | – | – | – | – | – | – | – | – |
| valid_post_repair | 112 | 1.000 | 0.759 | -0.241 | [-0.321, -0.161] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
