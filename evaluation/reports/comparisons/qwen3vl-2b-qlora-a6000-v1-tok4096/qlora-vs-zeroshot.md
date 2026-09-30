# Paired comparison

- A: `F:\vigraph\output\eval\qwen3-vl-2b-instruct-zeroshot-tok4096-s0`
- B: `F:\vigraph\output\eval\qwen3vl-2b-qlora-a6000-v1-tok4096-s0`
- 112 paired samples. Δ = B − A. Primary test: paired bootstrap (10,000 resamples, 95% CI); Holm-adjusted across the metrics below. Paired t-test and Wilcoxon signed-rank for reference.

| Metric | n | A | B | Δ | 95% CI | p (bootstrap) | p (Holm) | p (t) | p (Wilcoxon) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| node_f1 | 112 | 0.736 | 0.844 | +0.108 | [+0.048, +0.170] | 0.0005 | 0.0015 | 0.0007 | 0.0010 |
| edge_f1 | 112 | 0.502 | 0.624 | +0.121 | [+0.076, +0.171] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| edge_strict_f1 | 112 | 0.432 | 0.591 | +0.158 | [+0.115, +0.205] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| graph_similarity | 112 | 0.601 | 0.727 | +0.125 | [+0.083, +0.167] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| label_accuracy | 83 | 0.972 | 0.996 | +0.024 | [+0.012, +0.039] | 0.0011 | 0.0022 | 0.0008 | 0.0003 |
| qa_accuracy | 112 | 0.454 | 0.562 | +0.108 | [+0.061, +0.155] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| diagram_type_accuracy | 112 | 0.339 | 0.866 | +0.527 | [+0.429, +0.625] | 0.0001 | 0.0009 | 0.0000 | 0.0000 |
| valid_first_attempt | 112 | 0.536 | 0.670 | +0.134 | [+0.018, +0.250] | 0.0305 | 0.0305 | 0.0280 | 0.0287 |
| valid_post_repair | 112 | 0.759 | 0.893 | +0.134 | [+0.062, +0.205] | 0.0003 | 0.0012 | 0.0004 | 0.0006 |
