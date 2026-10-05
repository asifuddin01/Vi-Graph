# Paired comparison

- A: `/home/user/Vi-Graph/evaluation/reports/baseline-v1-final`
- B: `/home/user/Vi-Graph/evaluation/reports/qwen3vl-2b-qlora-a6000-v1-final-greedy`
- 500 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 500 | 0.872 | 0.854 | -0.017 | [-0.038, +0.002] | 0.0837 | 0.1674 | 0.0866 | 0.0026 |
| edge_f1 | 500 | 0.610 | 0.638 | +0.029 | [+0.005, +0.053] | 0.0211 | 0.0633 | 0.0185 | 0.1118 |
| edge_strict_f1 | 500 | 0.562 | 0.611 | +0.049 | [+0.025, +0.073] | 0.0002 | 0.0008 | 0.0001 | 0.0005 |
| graph_similarity | 500 | 0.738 | 0.740 | +0.002 | [-0.016, +0.019] | 0.8414 | 0.8414 | 0.8378 | 0.0144 |
| label_accuracy | 451 | 0.909 | 0.984 | +0.075 | [+0.064, +0.087] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| qa_accuracy | 500 | 0.450 | 0.582 | +0.132 | [+0.108, +0.156] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| diagram_type_accuracy | 500 | 0.702 | 0.882 | +0.180 | [+0.134, +0.226] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
| valid_first_attempt | 0 | – | – | – | – | – | – | – | – |
| valid_post_repair | 500 | 0.998 | 0.910 | -0.088 | [-0.114, -0.064] | 0.0001 | 0.0008 | 0.0000 | 0.0000 |
