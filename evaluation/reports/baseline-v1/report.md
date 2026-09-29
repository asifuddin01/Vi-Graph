# Evaluation run `baseline-v1`

- Predictor: `baseline:v1`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `2c67f24b3b83`
- Graph produced for 500 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.931 | 0.121 | 500 |
| Edge F1 | 0.635 | 0.303 | 500 |
| Edge F1 (strict) | 0.584 | 0.359 | 500 |
| Graph similarity | 0.781 | 0.184 | 500 |
| Label accuracy | 0.960 | 0.104 | 499 |
| Structural QA | 0.462 | 0.315 | 500 |
| Diagram type | 0.738 | 0.440 | 500 |
| Valid (first attempt) | – | – | 0 |
| Valid (bare JSON) | – | – | 0 |
| Valid (post-repair) | 1.000 | 0.000 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.926 | 0.896 | 0.911 | 7901 | 627 | 919 |
| Edges | 0.697 | 0.563 | 0.623 | 5005 | 2178 | 3884 |
| Edges (strict) | 0.655 | 0.529 | 0.585 | 4702 | 2481 | 4187 |

## Labels, edge text, grouping (matched items only)

- Labels (7901 matched): exact 0.942, case-insensitive 0.944, similarity 0.991, CER 0.009, WER 0.042
- Edge text (452 labeled edges matched): accuracy 0.031; lost 383, wrong 55, hallucinated 210
- Grouping (7901 matched nodes): accuracy 0.826; flattened 1224, wrongly nested 21, wrong group 131

## Structural QA (§20.7): 0.452 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.550 |
| predecessors | 500 | 0.576 |
| sources | 500 | 0.268 |
| sinks | 500 | 0.254 |
| path_exists | 1000 | 0.637 |
| count_nodes | 500 | 0.598 |
| count_edges | 500 | 0.330 |
| group_members | 239 | 0.201 |
| merge_point | 356 | 0.287 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 0.977 | 0.697 | 0.649 | 0.845 | 0.998 | 0.670 | 1.000 |
| 2 | 125 | 0.926 | 0.646 | 0.587 | 0.782 | 0.984 | 0.505 | 1.000 |
| 3 | 125 | 0.948 | 0.647 | 0.589 | 0.790 | 0.980 | 0.378 | 1.000 |
| 4 | 125 | 0.875 | 0.552 | 0.513 | 0.709 | 0.876 | 0.295 | 1.000 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.942 | 0.724 | 0.724 | 0.838 | 0.966 | 0.542 | 1.000 |
| flowchart | 72 | 0.902 | 0.564 | 0.564 | 0.739 | 0.929 | 0.401 | 1.000 |
| ml_pipeline | 72 | 0.923 | 0.678 | 0.678 | 0.805 | 0.967 | 0.494 | 1.000 |
| neural_network | 72 | 0.934 | 0.744 | 0.744 | 0.840 | 0.957 | 0.571 | 1.000 |
| scientific_workflow | 72 | 0.917 | 0.688 | 0.688 | 0.803 | 0.950 | 0.501 | 1.000 |
| system_architecture | 72 | 0.950 | 0.666 | 0.659 | 0.814 | 0.974 | 0.438 | 1.000 |
| uml | 68 | 0.952 | 0.369 | 0.000 | 0.623 | 0.977 | 0.276 | 1.000 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.963 | 0.828 | 0.742 | 0.880 | 0.981 | 0.746 | 1.000 |
| layered_tb | 325 | 0.934 | 0.685 | 0.658 | 0.808 | 0.948 | 0.457 | 1.000 |
| radial | 103 | 0.901 | 0.344 | 0.240 | 0.630 | 0.982 | 0.279 | 1.000 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.927 | 0.651 | 0.595 | 0.787 | 0.952 | 0.482 | 1.000 |
| dark | 158 | 0.945 | 0.624 | 0.582 | 0.785 | 0.957 | 0.442 | 1.000 |
| paper | 174 | 0.923 | 0.631 | 0.576 | 0.773 | 0.971 | 0.460 | 1.000 |

## Error taxonomy (§23; 500 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 919 | 1.84 | 241 |
| node hallucination | 627 | 1.25 | 221 |
| label corruption | 458 | 0.92 | 148 |
| wrong edge | 207 | 0.41 | 98 |
| missing edge | 3230 | 6.46 | 342 |
| reversed edge | 447 | 0.89 | 143 |
| branch confusion | 772 | 1.54 | 304 |
| merge confusion | 777 | 1.55 | 307 |
| edge label loss | 648 | 1.30 | 206 |
| grouping failure | 1376 | 2.75 | 184 |
| spurious edge | 1524 | 3.05 | 223 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 3051 · median 2247 · p90 6254 · p95 7408 · max 22715

## Reproducibility (§18.1)

- Predictor: baseline_version 1, tesseract 5.3.4, opencv 5.0.0, pytesseract 0.3.13, ink_window 21, ink_contrast 50, head_ratio 1.5
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1, git_commit f5849dde184776a37d34525e5faa2cd8a51e09a1
- Split `test` hash `2c67f24b3b83ae68c1df569d410e23292573c57f1f196659c76a8776696223b2`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-09-29 16:20 UTC, completed 2026-09-29 16:45 UTC
