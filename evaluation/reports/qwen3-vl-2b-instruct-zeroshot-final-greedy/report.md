# Evaluation run `qwen3-vl-2b-instruct-zeroshot-final-greedy`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 360 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.703 | 0.443 | 500 |
| Edge F1 | 0.499 | 0.409 | 500 |
| Edge F1 (strict) | 0.415 | 0.390 | 500 |
| Graph similarity | 0.581 | 0.389 | 500 |
| Label accuracy | 0.979 | 0.058 | 360 |
| Structural QA | 0.437 | 0.382 | 500 |
| Diagram type | 0.334 | 0.472 | 500 |
| Valid (first attempt) | 0.512 | 0.500 | 500 |
| Valid (bare JSON) | 0.000 | 0.000 | 500 |
| Valid (post-repair) | 0.720 | 0.449 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.955 | 0.449 | 0.610 | 3956 | 188 | 4864 |
| Edges | 0.607 | 0.275 | 0.378 | 2444 | 1583 | 6445 |
| Edges (strict) | 0.511 | 0.231 | 0.319 | 2057 | 1970 | 6832 |

## Labels, edge text, grouping (matched items only)

- Labels (3956 matched): exact 0.962, case-insensitive 0.970, similarity 0.994, CER 0.006, WER 0.026
- Edge text (248 labeled edges matched): accuracy 0.573; lost 42, wrong 64, hallucinated 624
- Grouping (3956 matched nodes): accuracy 0.807; flattened 759, wrongly nested 3, wrong group 0

## Output validity (§20.2)

- Status: valid_first_attempt 256, failed 140, repaired 70, valid_after_retry 34 · mean attempts 1.49 · with repairs 70 · truncated outputs 71
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.500, edge F1 0.357, graph similarity 0.414

## Structural QA (§20.7): 0.417 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.446 |
| predecessors | 500 | 0.458 |
| sources | 500 | 0.370 |
| sinks | 500 | 0.378 |
| path_exists | 1000 | 0.555 |
| count_nodes | 500 | 0.582 |
| count_edges | 500 | 0.352 |
| group_members | 239 | 0.008 |
| merge_point | 356 | 0.191 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 1.000 | 0.780 | 0.672 | 0.875 | 0.998 | 0.810 | 1.000 |
| 2 | 125 | 0.973 | 0.721 | 0.565 | 0.809 | 0.993 | 0.616 | 0.976 |
| 3 | 125 | 0.706 | 0.446 | 0.380 | 0.552 | 0.966 | 0.287 | 0.736 |
| 4 | 125 | 0.134 | 0.051 | 0.045 | 0.089 | 0.840 | 0.035 | 0.168 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.737 | 0.562 | 0.514 | 0.640 | 0.960 | 0.493 | 0.764 |
| flowchart | 72 | 0.707 | 0.469 | 0.446 | 0.581 | 0.976 | 0.450 | 0.722 |
| ml_pipeline | 72 | 0.664 | 0.513 | 0.471 | 0.575 | 0.987 | 0.421 | 0.681 |
| neural_network | 72 | 0.749 | 0.538 | 0.491 | 0.630 | 0.980 | 0.455 | 0.764 |
| scientific_workflow | 72 | 0.773 | 0.583 | 0.544 | 0.664 | 0.987 | 0.512 | 0.792 |
| system_architecture | 72 | 0.694 | 0.470 | 0.383 | 0.563 | 0.981 | 0.414 | 0.708 |
| uml | 68 | 0.591 | 0.352 | 0.039 | 0.406 | 0.983 | 0.306 | 0.603 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.925 | 0.762 | 0.685 | 0.823 | 0.990 | 0.690 | 0.931 |
| layered_tb | 325 | 0.620 | 0.487 | 0.396 | 0.528 | 0.970 | 0.396 | 0.643 |
| radial | 103 | 0.811 | 0.355 | 0.288 | 0.580 | 0.992 | 0.388 | 0.816 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.673 | 0.482 | 0.412 | 0.562 | 0.976 | 0.420 | 0.690 |
| dark | 158 | 0.687 | 0.485 | 0.420 | 0.568 | 0.982 | 0.423 | 0.703 |
| paper | 174 | 0.746 | 0.530 | 0.414 | 0.612 | 0.979 | 0.466 | 0.764 |

## Error taxonomy (§23; 360 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 247 | 0.69 | 65 |
| node hallucination | 188 | 0.52 | 46 |
| label corruption | 149 | 0.41 | 63 |
| wrong edge | 695 | 1.93 | 192 |
| missing edge | 715 | 1.99 | 162 |
| reversed edge | 245 | 0.68 | 91 |
| branch confusion | 348 | 0.97 | 174 |
| merge confusion | 454 | 1.26 | 203 |
| edge label loss | 730 | 2.03 | 119 |
| grouping failure | 762 | 2.12 | 131 |
| spurious edge | 643 | 1.79 | 157 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 43694 · median 29668 · p90 103001 · p95 107801 · max 121531

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `None`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 2048, seed 0; image max side 896
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-03 06:23 UTC, completed 2026-10-03 12:28 UTC
