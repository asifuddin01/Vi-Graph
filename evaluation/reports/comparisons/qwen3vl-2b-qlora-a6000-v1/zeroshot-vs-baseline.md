# Paired comparison

- A: `F:\vigraph\output\eval\baseline-v1-windows`
- B: `F:\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.865 | 0.712 | -0.153 | [-0.222, -0.088] | 0.0001 | 0.0008 | 0.0000 | 0.0059 |
| edge_f1 | 112 | 0.620 | 0.497 | -0.124 | [-0.183, -0.067] | 0.0002 | 0.0008 | 0.0001 | 0.0001 |
| edge_strict_f1 | 112 | 0.569 | 0.420 | -0.148 | [-0.203, -0.096] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| graph_similarity | 112 | 0.736 | 0.586 | -0.150 | [-0.205, -0.098] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| label_accuracy | 81 | 0.954 | 0.984 | +0.029 | [+0.015, +0.046] | 0.0009 | 0.0018 | 0.0005 | 0.0002 |
| qa_accuracy | 112 | 0.447 | 0.451 | +0.004 | [-0.043, +0.052] | 0.8626 | 0.8626 | 0.8646 | 0.9597 |
| diagram_type_accuracy | 112 | 0.732 | 0.321 | -0.411 | [-0.536, -0.286] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| valid_first_attempt | 0 | – | – | – | – | – | – | – | – |
| valid_post_repair | 112 | 1.000 | 0.723 | -0.277 | [-0.357, -0.196] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
