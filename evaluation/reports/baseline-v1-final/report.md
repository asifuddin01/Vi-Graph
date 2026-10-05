# Evaluation run `baseline-v1-final`

- Predictor: `baseline:v1`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 499 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.872 | 0.221 | 500 |
| Edge F1 | 0.610 | 0.337 | 500 |
| Edge F1 (strict) | 0.562 | 0.382 | 500 |
| Graph similarity | 0.738 | 0.251 | 500 |
| Label accuracy | 0.885 | 0.187 | 495 |
| Structural QA | 0.450 | 0.355 | 500 |
| Diagram type | 0.702 | 0.458 | 500 |
| Valid (first attempt) | – | – | 0 |
| Valid (bare JSON) | – | – | 0 |
| Valid (post-repair) | 0.998 | 0.045 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.844 | 0.756 | 0.798 | 6671 | 1232 | 2149 |
| Edges | 0.608 | 0.430 | 0.504 | 3821 | 2460 | 5068 |
| Edges (strict) | 0.567 | 0.401 | 0.470 | 3563 | 2718 | 5326 |

## Labels, edge text, grouping (matched items only)

- Labels (6671 matched): exact 0.856, case-insensitive 0.862, similarity 0.978, CER 0.022, WER 0.108
- Edge text (310 labeled edges matched): accuracy 0.026; lost 249, wrong 53, hallucinated 155
- Grouping (6671 matched nodes): accuracy 0.832; flattened 973, wrongly nested 25, wrong group 126

## Structural QA (§20.7): 0.433 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.534 |
| predecessors | 500 | 0.538 |
| sources | 500 | 0.294 |
| sinks | 500 | 0.294 |
| path_exists | 1000 | 0.596 |
| count_nodes | 500 | 0.562 |
| count_edges | 500 | 0.314 |
| group_members | 239 | 0.146 |
| merge_point | 356 | 0.250 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 0.989 | 0.825 | 0.770 | 0.904 | 0.995 | 0.789 | 1.000 |
| 2 | 125 | 0.936 | 0.666 | 0.617 | 0.804 | 0.967 | 0.516 | 1.000 |
| 3 | 125 | 0.926 | 0.632 | 0.575 | 0.773 | 0.904 | 0.342 | 1.000 |
| 4 | 125 | 0.637 | 0.316 | 0.287 | 0.472 | 0.665 | 0.153 | 0.992 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.860 | 0.659 | 0.659 | 0.764 | 0.866 | 0.520 | 1.000 |
| flowchart | 72 | 0.835 | 0.582 | 0.582 | 0.714 | 0.843 | 0.413 | 1.000 |
| ml_pipeline | 72 | 0.842 | 0.648 | 0.648 | 0.746 | 0.893 | 0.478 | 1.000 |
| neural_network | 72 | 0.872 | 0.690 | 0.690 | 0.779 | 0.868 | 0.530 | 1.000 |
| scientific_workflow | 72 | 0.871 | 0.681 | 0.681 | 0.775 | 0.888 | 0.525 | 1.000 |
| system_architecture | 72 | 0.895 | 0.647 | 0.645 | 0.775 | 0.901 | 0.430 | 1.000 |
| uml | 68 | 0.932 | 0.345 | 0.000 | 0.608 | 0.941 | 0.242 | 0.985 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.955 | 0.812 | 0.742 | 0.871 | 0.970 | 0.723 | 0.986 |
| layered_tb | 325 | 0.838 | 0.598 | 0.574 | 0.718 | 0.842 | 0.396 | 1.000 |
| radial | 103 | 0.921 | 0.505 | 0.399 | 0.709 | 0.960 | 0.429 | 1.000 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.858 | 0.620 | 0.572 | 0.736 | 0.884 | 0.473 | 1.000 |
| dark | 158 | 0.889 | 0.610 | 0.564 | 0.748 | 0.884 | 0.443 | 1.000 |
| paper | 174 | 0.870 | 0.600 | 0.551 | 0.731 | 0.887 | 0.434 | 0.994 |

## Error taxonomy (§23; 499 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 2109 | 4.23 | 271 |
| node hallucination | 1232 | 2.47 | 232 |
| label corruption | 958 | 1.92 | 229 |
| wrong edge | 265 | 0.53 | 121 |
| missing edge | 4369 | 8.76 | 344 |
| reversed edge | 402 | 0.81 | 117 |
| branch confusion | 710 | 1.42 | 293 |
| merge confusion | 733 | 1.47 | 301 |
| edge label loss | 457 | 0.92 | 200 |
| grouping failure | 1124 | 2.25 | 179 |
| spurious edge | 1793 | 3.59 | 228 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 2754 · median 2039 · p90 5731 · p95 6602 · max 18102

## Reproducibility (§18.1)

- Predictor: baseline_version 1, tesseract 5.3.4, opencv 5.0.0, pytesseract 0.3.13, ink_window 21, ink_contrast 50, head_ratio 1.5
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1, git_commit f5cfda76104d56d183701ac100b362f8b8a1d74c
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-05 03:44 UTC, completed 2026-10-05 04:07 UTC
