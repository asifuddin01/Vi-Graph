# Evaluation run `qwen3-vl-2b-instruct-zeroshot-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 81 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.712 | 0.444 | 112 |
| Edge F1 | 0.497 | 0.403 | 112 |
| Edge F1 (strict) | 0.420 | 0.393 | 112 |
| Graph similarity | 0.586 | 0.388 | 112 |
| Label accuracy | 0.984 | 0.050 | 81 |
| Structural QA | 0.451 | 0.375 | 112 |
| Diagram type | 0.321 | 0.469 | 112 |
| Valid (first attempt) | 0.509 | 0.502 | 112 |
| Valid (bare JSON) | 0.000 | 0.000 | 112 |
| Valid (post-repair) | 0.723 | 0.449 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.974 | 0.447 | 0.612 | 873 | 23 | 1082 |
| Edges | 0.624 | 0.280 | 0.387 | 547 | 329 | 1404 |
| Edges (strict) | 0.538 | 0.241 | 0.333 | 471 | 405 | 1480 |

## Labels, edge text, grouping (matched items only)

- Labels (873 matched): exact 0.969, case-insensitive 0.974, similarity 0.994, CER 0.005, WER 0.024
- Edge text (45 labeled edges matched): accuracy 0.556; lost 6, wrong 14, hallucinated 150
- Grouping (873 matched nodes): accuracy 0.805; flattened 169, wrongly nested 1, wrong group 0

## Output validity (§20.2)

- Status: valid_first_attempt 57, failed 31, repaired 15, valid_after_retry 9 · mean attempts 1.49 · with repairs 15 · truncated outputs 33
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.501, edge F1 0.345, graph similarity 0.411

## Structural QA (§20.7): 0.433 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.464 |
| predecessors | 112 | 0.482 |
| sources | 112 | 0.438 |
| sinks | 112 | 0.366 |
| path_exists | 224 | 0.585 |
| count_nodes | 112 | 0.598 |
| count_edges | 112 | 0.348 |
| group_members | 56 | 0.018 |
| merge_point | 78 | 0.154 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 1.000 | 0.787 | 0.679 | 0.875 | 1.000 | 0.813 | 1.000 |
| 2 | 28 | 1.000 | 0.657 | 0.542 | 0.802 | 0.996 | 0.585 | 1.000 |
| 3 | 28 | 0.819 | 0.526 | 0.445 | 0.647 | 0.964 | 0.402 | 0.857 |
| 4 | 28 | 0.028 | 0.016 | 0.016 | 0.022 | 0.640 | 0.004 | 0.036 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.675 | 0.497 | 0.479 | 0.581 | 0.960 | 0.491 | 0.688 |
| flowchart | 16 | 0.681 | 0.326 | 0.316 | 0.503 | 0.975 | 0.412 | 0.688 |
| ml_pipeline | 16 | 0.738 | 0.595 | 0.563 | 0.657 | 0.972 | 0.442 | 0.750 |
| neural_network | 16 | 0.734 | 0.508 | 0.508 | 0.620 | 0.981 | 0.445 | 0.750 |
| scientific_workflow | 16 | 0.747 | 0.602 | 0.561 | 0.664 | 1.000 | 0.553 | 0.750 |
| system_architecture | 16 | 0.731 | 0.542 | 0.452 | 0.612 | 1.000 | 0.486 | 0.750 |
| uml | 16 | 0.676 | 0.406 | 0.065 | 0.468 | 0.996 | 0.328 | 0.688 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.922 | 0.656 | 0.544 | 0.751 | 0.997 | 0.589 | 0.933 |
| layered_tb | 71 | 0.618 | 0.497 | 0.418 | 0.537 | 0.974 | 0.412 | 0.634 |
| radial | 26 | 0.846 | 0.402 | 0.357 | 0.626 | 0.995 | 0.478 | 0.846 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.679 | 0.452 | 0.387 | 0.554 | 0.988 | 0.427 | 0.686 |
| dark | 33 | 0.710 | 0.488 | 0.453 | 0.583 | 0.981 | 0.428 | 0.727 |
| paper | 44 | 0.739 | 0.538 | 0.422 | 0.615 | 0.982 | 0.488 | 0.750 |

## Error taxonomy (§23; 81 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 38 | 0.47 | 14 |
| node hallucination | 23 | 0.28 | 7 |
| label corruption | 27 | 0.33 | 13 |
| wrong edge | 137 | 1.69 | 46 |
| missing edge | 114 | 1.41 | 36 |
| reversed edge | 67 | 0.83 | 21 |
| branch confusion | 81 | 1.00 | 42 |
| merge confusion | 103 | 1.27 | 47 |
| edge label loss | 170 | 2.10 | 28 |
| grouping failure | 170 | 2.10 | 31 |
| spurious edge | 125 | 1.54 | 36 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 79720 · median 50580 · p90 183611 · p95 186201 · max 273936

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `None`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 2048, seed 0; image max side 896
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-09-30 02:50 UTC, completed 2026-09-30 05:20 UTC
