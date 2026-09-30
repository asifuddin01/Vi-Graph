# Evaluation run `baseline-v1-windows`

- Predictor: `baseline:v1`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 112 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.865 | 0.234 | 112 |
| Edge F1 | 0.620 | 0.344 | 112 |
| Edge F1 (strict) | 0.569 | 0.393 | 112 |
| Graph similarity | 0.736 | 0.265 | 112 |
| Label accuracy | 0.878 | 0.205 | 111 |
| Structural QA | 0.447 | 0.349 | 112 |
| Diagram type | 0.732 | 0.445 | 112 |
| Valid (first attempt) | – | – | 0 |
| Valid (bare JSON) | – | – | 0 |
| Valid (post-repair) | 1.000 | 0.000 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.837 | 0.755 | 0.794 | 1477 | 287 | 478 |
| Edges | 0.637 | 0.448 | 0.526 | 874 | 498 | 1077 |
| Edges (strict) | 0.593 | 0.417 | 0.490 | 814 | 558 | 1137 |

## Labels, edge text, grouping (matched items only)

- Labels (1477 matched): exact 0.862, case-insensitive 0.869, similarity 0.978, CER 0.021, WER 0.102
- Edge text (80 labeled edges matched): accuracy 0.037; lost 66, wrong 11, hallucinated 32
- Grouping (1477 matched nodes): accuracy 0.831; flattened 221, wrongly nested 5, wrong group 24

## Structural QA (§20.7): 0.432 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.491 |
| predecessors | 112 | 0.589 |
| sources | 112 | 0.286 |
| sinks | 112 | 0.295 |
| path_exists | 224 | 0.607 |
| count_nodes | 112 | 0.562 |
| count_edges | 112 | 0.286 |
| group_members | 56 | 0.179 |
| merge_point | 78 | 0.231 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 0.988 | 0.859 | 0.797 | 0.913 | 1.000 | 0.809 | 1.000 |
| 2 | 28 | 0.916 | 0.627 | 0.557 | 0.765 | 0.967 | 0.470 | 1.000 |
| 3 | 28 | 0.942 | 0.675 | 0.623 | 0.800 | 0.894 | 0.357 | 1.000 |
| 4 | 28 | 0.614 | 0.321 | 0.297 | 0.465 | 0.643 | 0.152 | 1.000 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.818 | 0.635 | 0.635 | 0.726 | 0.854 | 0.552 | 1.000 |
| flowchart | 16 | 0.816 | 0.506 | 0.506 | 0.661 | 0.816 | 0.368 | 1.000 |
| ml_pipeline | 16 | 0.795 | 0.693 | 0.693 | 0.745 | 0.857 | 0.506 | 1.000 |
| neural_network | 16 | 0.890 | 0.622 | 0.622 | 0.757 | 0.869 | 0.465 | 1.000 |
| scientific_workflow | 16 | 0.924 | 0.747 | 0.747 | 0.835 | 0.913 | 0.533 | 1.000 |
| system_architecture | 16 | 0.938 | 0.783 | 0.777 | 0.859 | 0.925 | 0.484 | 1.000 |
| uml | 16 | 0.875 | 0.357 | 0.000 | 0.570 | 0.913 | 0.221 | 1.000 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.919 | 0.756 | 0.602 | 0.800 | 0.949 | 0.619 | 1.000 |
| layered_tb | 71 | 0.839 | 0.635 | 0.599 | 0.733 | 0.834 | 0.416 | 1.000 |
| radial | 26 | 0.903 | 0.502 | 0.467 | 0.707 | 0.957 | 0.433 | 1.000 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.917 | 0.675 | 0.613 | 0.784 | 0.937 | 0.480 | 1.000 |
| dark | 33 | 0.852 | 0.638 | 0.615 | 0.739 | 0.824 | 0.456 | 1.000 |
| paper | 44 | 0.833 | 0.564 | 0.499 | 0.695 | 0.872 | 0.414 | 1.000 |

## Error taxonomy (§23; 112 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 478 | 4.27 | 64 |
| node hallucination | 287 | 2.56 | 48 |
| label corruption | 204 | 1.82 | 52 |
| wrong edge | 46 | 0.41 | 22 |
| missing edge | 920 | 8.21 | 80 |
| reversed edge | 111 | 0.99 | 28 |
| branch confusion | 161 | 1.44 | 66 |
| merge confusion | 152 | 1.36 | 69 |
| edge label loss | 109 | 0.97 | 44 |
| grouping failure | 250 | 2.23 | 41 |
| spurious edge | 341 | 3.04 | 49 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 2491 · median 1599 · p90 4763 · p95 5948 · max 21392

## Reproducibility (§18.1)

- Predictor: baseline_version 1, tesseract 5.4.0.20240606, opencv 5.0.0, pytesseract 0.3.13, ink_window 21, ink_contrast 50, head_ratio 1.5
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-09-30 07:49 UTC, completed 2026-09-30 07:53 UTC
