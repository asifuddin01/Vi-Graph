# Evaluation run `qwen3-vl-2b-instruct-zeroshot-final-t0.7-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 363 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.708 | 0.440 | 500 |
| Edge F1 | 0.495 | 0.406 | 500 |
| Edge F1 (strict) | 0.409 | 0.387 | 500 |
| Graph similarity | 0.581 | 0.385 | 500 |
| Label accuracy | 0.977 | 0.061 | 363 |
| Structural QA | 0.440 | 0.380 | 500 |
| Diagram type | 0.342 | 0.475 | 500 |
| Valid (first attempt) | 0.514 | 0.500 | 500 |
| Valid (bare JSON) | 0.000 | 0.000 | 500 |
| Valid (post-repair) | 0.726 | 0.446 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.953 | 0.454 | 0.615 | 4005 | 196 | 4815 |
| Edges | 0.587 | 0.275 | 0.375 | 2446 | 1722 | 6443 |
| Edges (strict) | 0.491 | 0.230 | 0.313 | 2046 | 2122 | 6843 |

## Labels, edge text, grouping (matched items only)

- Labels (4005 matched): exact 0.958, case-insensitive 0.965, similarity 0.993, CER 0.007, WER 0.031
- Edge text (238 labeled edges matched): accuracy 0.559; lost 47, wrong 58, hallucinated 598
- Grouping (4005 matched nodes): accuracy 0.811; flattened 750, wrongly nested 6, wrong group 0

## Output validity (§20.2)

- Status: valid_first_attempt 257, failed 137, repaired 62, valid_after_retry 44 · mean attempts 1.49 · with repairs 62 · truncated outputs 64
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.503, edge F1 0.358, graph similarity 0.416

## Structural QA (§20.7): 0.421 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.444 |
| predecessors | 500 | 0.448 |
| sources | 500 | 0.378 |
| sinks | 500 | 0.360 |
| path_exists | 1000 | 0.575 |
| count_nodes | 500 | 0.574 |
| count_edges | 500 | 0.370 |
| group_members | 239 | 0.004 |
| merge_point | 356 | 0.199 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 0.992 | 0.770 | 0.668 | 0.869 | 1.000 | 0.811 | 0.992 |
| 2 | 125 | 0.995 | 0.729 | 0.560 | 0.822 | 0.994 | 0.630 | 1.000 |
| 3 | 125 | 0.716 | 0.428 | 0.362 | 0.546 | 0.961 | 0.286 | 0.744 |
| 4 | 125 | 0.131 | 0.055 | 0.048 | 0.089 | 0.814 | 0.035 | 0.168 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.771 | 0.567 | 0.512 | 0.657 | 0.960 | 0.502 | 0.792 |
| flowchart | 72 | 0.692 | 0.460 | 0.431 | 0.567 | 0.974 | 0.436 | 0.708 |
| ml_pipeline | 72 | 0.673 | 0.523 | 0.474 | 0.584 | 0.978 | 0.447 | 0.694 |
| neural_network | 72 | 0.748 | 0.526 | 0.473 | 0.620 | 0.978 | 0.468 | 0.764 |
| scientific_workflow | 72 | 0.786 | 0.584 | 0.549 | 0.673 | 0.978 | 0.511 | 0.819 |
| system_architecture | 72 | 0.684 | 0.473 | 0.371 | 0.555 | 0.986 | 0.422 | 0.694 |
| uml | 68 | 0.598 | 0.327 | 0.034 | 0.404 | 0.991 | 0.287 | 0.603 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.859 | 0.727 | 0.667 | 0.776 | 0.991 | 0.692 | 0.861 |
| layered_tb | 325 | 0.639 | 0.489 | 0.393 | 0.537 | 0.965 | 0.398 | 0.665 |
| radial | 103 | 0.822 | 0.355 | 0.280 | 0.586 | 0.998 | 0.398 | 0.825 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.704 | 0.491 | 0.414 | 0.579 | 0.976 | 0.442 | 0.720 |
| dark | 158 | 0.682 | 0.478 | 0.411 | 0.563 | 0.979 | 0.417 | 0.696 |
| paper | 174 | 0.737 | 0.516 | 0.403 | 0.600 | 0.977 | 0.460 | 0.759 |

## Error taxonomy (§23; 363 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 274 | 0.75 | 65 |
| node hallucination | 196 | 0.54 | 58 |
| label corruption | 170 | 0.47 | 71 |
| wrong edge | 764 | 2.10 | 194 |
| missing edge | 712 | 1.96 | 164 |
| reversed edge | 252 | 0.69 | 91 |
| branch confusion | 356 | 0.98 | 182 |
| merge confusion | 468 | 1.29 | 205 |
| edge label loss | 703 | 1.94 | 118 |
| grouping failure | 756 | 2.08 | 137 |
| spurious edge | 706 | 1.94 | 165 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 43706 · median 30989 · p90 102819 · p95 105292 · max 122867

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `None`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.7, top_p 0.8, max_new_tokens 2048, seed 0; image max side 896
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-03 19:23 UTC, completed 2026-10-04 01:28 UTC
