# Run-to-run variance: 3 runs (seeds [0, 1, 2]), 500 samples each

Mean ± std of the per-run means.

| Metric | Mean | Std |
| --- | --- | --- |
| node_f1 | 0.708 | 0.012 |
| edge_f1 | 0.495 | 0.009 |
| edge_strict_f1 | 0.411 | 0.005 |
| graph_similarity | 0.582 | 0.009 |
| label_accuracy | 0.978 | 0.002 |
| qa_accuracy | 0.441 | 0.010 |
| diagram_type_accuracy | 0.342 | 0.010 |
| valid_first_attempt | 0.507 | 0.009 |
| valid_post_repair | 0.727 | 0.012 |

## By level

| Level | node_f1 | edge_f1 | graph_similarity | qa_accuracy |
| --- | --- | --- | --- | --- |
| 1 | 0.997 ± 0.005 | 0.771 ± 0.005 | 0.871 ± 0.003 | 0.815 ± 0.012 |
| 2 | 0.977 ± 0.015 | 0.723 ± 0.006 | 0.812 ± 0.009 | 0.620 ± 0.009 |
| 3 | 0.737 ± 0.047 | 0.435 ± 0.030 | 0.561 ± 0.036 | 0.295 ± 0.027 |
| 4 | 0.121 ± 0.011 | 0.051 ± 0.003 | 0.083 ± 0.007 | 0.034 ± 0.001 |
