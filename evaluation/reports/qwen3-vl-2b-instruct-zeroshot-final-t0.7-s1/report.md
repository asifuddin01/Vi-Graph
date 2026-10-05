# Evaluation run `qwen3-vl-2b-instruct-zeroshot-final-t0.7-s1`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 358 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.696 | 0.446 | 500 |
| Edge F1 | 0.486 | 0.408 | 500 |
| Edge F1 (strict) | 0.407 | 0.392 | 500 |
| Graph similarity | 0.572 | 0.390 | 500 |
| Label accuracy | 0.976 | 0.080 | 358 |
| Structural QA | 0.431 | 0.383 | 500 |
| Diagram type | 0.332 | 0.471 | 500 |
| Valid (first attempt) | 0.496 | 0.500 | 500 |
| Valid (bare JSON) | 0.000 | 0.000 | 500 |
| Valid (post-repair) | 0.716 | 0.451 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.948 | 0.439 | 0.600 | 3872 | 214 | 4948 |
| Edges | 0.582 | 0.262 | 0.361 | 2328 | 1669 | 6561 |
| Edges (strict) | 0.491 | 0.221 | 0.305 | 1962 | 2035 | 6927 |

## Labels, edge text, grouping (matched items only)

- Labels (3872 matched): exact 0.965, case-insensitive 0.971, similarity 0.994, CER 0.006, WER 0.026
- Edge text (223 labeled edges matched): accuracy 0.552; lost 47, wrong 53, hallucinated 602
- Grouping (3872 matched nodes): accuracy 0.816; flattened 702, wrongly nested 11, wrong group 1

## Output validity (§20.2)

- Status: valid_first_attempt 248, failed 142, repaired 79, valid_after_retry 31 · mean attempts 1.50 · with repairs 79 · truncated outputs 77
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.487, edge F1 0.346, graph similarity 0.403

## Structural QA (§20.7): 0.411 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.442 |
| predecessors | 500 | 0.450 |
| sources | 500 | 0.368 |
| sinks | 500 | 0.364 |
| path_exists | 1000 | 0.553 |
| count_nodes | 500 | 0.558 |
| count_edges | 500 | 0.364 |
| group_members | 239 | 0.004 |
| merge_point | 356 | 0.177 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 1.000 | 0.767 | 0.670 | 0.871 | 1.000 | 0.805 | 1.000 |
| 2 | 125 | 0.972 | 0.718 | 0.571 | 0.809 | 0.992 | 0.611 | 0.976 |
| 3 | 125 | 0.705 | 0.408 | 0.347 | 0.534 | 0.962 | 0.274 | 0.736 |
| 4 | 125 | 0.109 | 0.049 | 0.041 | 0.076 | 0.792 | 0.034 | 0.152 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.727 | 0.533 | 0.491 | 0.622 | 0.975 | 0.480 | 0.736 |
| flowchart | 72 | 0.680 | 0.451 | 0.427 | 0.558 | 0.954 | 0.427 | 0.708 |
| ml_pipeline | 72 | 0.674 | 0.521 | 0.485 | 0.586 | 0.974 | 0.441 | 0.708 |
| neural_network | 72 | 0.719 | 0.503 | 0.456 | 0.598 | 0.979 | 0.430 | 0.736 |
| scientific_workflow | 72 | 0.754 | 0.553 | 0.529 | 0.644 | 0.980 | 0.493 | 0.778 |
| system_architecture | 72 | 0.668 | 0.478 | 0.390 | 0.553 | 0.985 | 0.432 | 0.681 |
| uml | 68 | 0.649 | 0.355 | 0.054 | 0.439 | 0.990 | 0.305 | 0.662 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.926 | 0.762 | 0.684 | 0.821 | 0.989 | 0.710 | 0.931 |
| layered_tb | 325 | 0.606 | 0.469 | 0.385 | 0.514 | 0.963 | 0.388 | 0.634 |
| radial | 103 | 0.821 | 0.345 | 0.283 | 0.582 | 0.998 | 0.371 | 0.825 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.671 | 0.470 | 0.405 | 0.555 | 0.976 | 0.420 | 0.685 |
| dark | 158 | 0.689 | 0.484 | 0.417 | 0.569 | 0.973 | 0.421 | 0.715 |
| paper | 174 | 0.727 | 0.502 | 0.401 | 0.593 | 0.980 | 0.450 | 0.747 |

## Error taxonomy (§23; 358 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 293 | 0.82 | 68 |
| node hallucination | 214 | 0.60 | 52 |
| label corruption | 134 | 0.37 | 68 |
| wrong edge | 698 | 1.95 | 191 |
| missing edge | 756 | 2.11 | 152 |
| reversed edge | 248 | 0.69 | 94 |
| branch confusion | 362 | 1.01 | 179 |
| merge confusion | 448 | 1.25 | 200 |
| edge label loss | 702 | 1.96 | 121 |
| grouping failure | 714 | 1.99 | 130 |
| spurious edge | 723 | 2.02 | 168 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 45577 · median 30717 · p90 106227 · p95 110136 · max 119991

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `None`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.7, top_p 0.8, max_new_tokens 2048, seed 1; image max side 896
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-04 06:44 UTC, completed 2026-10-04 13:04 UTC
