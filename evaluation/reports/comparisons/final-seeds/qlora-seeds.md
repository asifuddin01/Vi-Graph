# Run-to-run variance: 3 runs (seeds [0, 1, 2]), 500 samples each

Mean ± std of the per-run means.

| Metric | Mean | Std |
| --- | --- | --- |
| node_f1 | 0.869 | 0.007 |
| edge_f1 | 0.639 | 0.004 |
| edge_strict_f1 | 0.614 | 0.006 |
| graph_similarity | 0.748 | 0.006 |
| label_accuracy | 0.980 | 0.001 |
| qa_accuracy | 0.581 | 0.005 |
| diagram_type_accuracy | 0.909 | 0.004 |
| valid_first_attempt | 0.718 | 0.011 |
| valid_post_repair | 0.937 | 0.005 |

## By level

| Level | node_f1 | edge_f1 | graph_similarity | qa_accuracy |
| --- | --- | --- | --- | --- |
| 1 | 1.000 ± 0.000 | 0.909 ± 0.008 | 0.955 ± 0.004 | 0.905 ± 0.005 |
| 2 | 0.990 ± 0.000 | 0.835 ± 0.006 | 0.907 ± 0.003 | 0.786 ± 0.010 |
| 3 | 0.928 ± 0.007 | 0.590 ± 0.012 | 0.751 ± 0.010 | 0.458 ± 0.011 |
| 4 | 0.556 ± 0.025 | 0.220 ± 0.011 | 0.381 ± 0.017 | 0.175 ± 0.006 |
