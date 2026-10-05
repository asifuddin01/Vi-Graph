# Evaluation run `qwen3-vl-2b-instruct-zeroshot-final-t0.7-s2`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 370 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.720 | 0.434 | 500 |
| Edge F1 | 0.504 | 0.408 | 500 |
| Edge F1 (strict) | 0.417 | 0.388 | 500 |
| Graph similarity | 0.591 | 0.381 | 500 |
| Label accuracy | 0.981 | 0.053 | 370 |
| Structural QA | 0.452 | 0.379 | 500 |
| Diagram type | 0.352 | 0.478 | 500 |
| Valid (first attempt) | 0.510 | 0.500 | 500 |
| Valid (bare JSON) | 0.000 | 0.000 | 500 |
| Valid (post-repair) | 0.740 | 0.439 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.954 | 0.468 | 0.628 | 4124 | 197 | 4696 |
| Edges | 0.584 | 0.280 | 0.379 | 2490 | 1774 | 6399 |
| Edges (strict) | 0.487 | 0.233 | 0.316 | 2075 | 2189 | 6814 |

## Labels, edge text, grouping (matched items only)

- Labels (4124 matched): exact 0.966, case-insensitive 0.972, similarity 0.994, CER 0.006, WER 0.023
- Edge text (249 labeled edges matched): accuracy 0.602; lost 52, wrong 47, hallucinated 594
- Grouping (4124 matched nodes): accuracy 0.805; flattened 798, wrongly nested 5, wrong group 0

## Output validity (§20.2)

- Status: valid_first_attempt 255, failed 130, repaired 73, valid_after_retry 42 · mean attempts 1.49 · with repairs 73 · truncated outputs 62
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.498, edge F1 0.355, graph similarity 0.412

## Structural QA (§20.7): 0.432 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.464 |
| predecessors | 500 | 0.452 |
| sources | 500 | 0.406 |
| sinks | 500 | 0.376 |
| path_exists | 1000 | 0.591 |
| count_nodes | 500 | 0.578 |
| count_edges | 500 | 0.374 |
| group_members | 239 | 0.008 |
| merge_point | 356 | 0.194 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 1.000 | 0.777 | 0.666 | 0.874 | 1.000 | 0.829 | 1.000 |
| 2 | 125 | 0.966 | 0.722 | 0.566 | 0.806 | 0.994 | 0.618 | 0.968 |
| 3 | 125 | 0.791 | 0.468 | 0.392 | 0.602 | 0.965 | 0.325 | 0.824 |
| 4 | 125 | 0.124 | 0.049 | 0.042 | 0.083 | 0.863 | 0.035 | 0.168 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.749 | 0.562 | 0.508 | 0.645 | 0.979 | 0.509 | 0.764 |
| flowchart | 72 | 0.730 | 0.469 | 0.446 | 0.594 | 0.974 | 0.468 | 0.750 |
| ml_pipeline | 72 | 0.688 | 0.528 | 0.476 | 0.591 | 0.987 | 0.448 | 0.708 |
| neural_network | 72 | 0.746 | 0.534 | 0.482 | 0.623 | 0.979 | 0.460 | 0.778 |
| scientific_workflow | 72 | 0.756 | 0.557 | 0.520 | 0.644 | 0.977 | 0.498 | 0.792 |
| system_architecture | 72 | 0.724 | 0.523 | 0.421 | 0.600 | 0.981 | 0.454 | 0.736 |
| uml | 68 | 0.643 | 0.344 | 0.044 | 0.433 | 0.991 | 0.317 | 0.647 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.941 | 0.784 | 0.701 | 0.840 | 0.992 | 0.713 | 0.944 |
| layered_tb | 325 | 0.638 | 0.493 | 0.397 | 0.539 | 0.970 | 0.407 | 0.668 |
| radial | 103 | 0.824 | 0.344 | 0.279 | 0.583 | 0.998 | 0.410 | 0.825 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.702 | 0.491 | 0.416 | 0.578 | 0.979 | 0.437 | 0.726 |
| dark | 158 | 0.715 | 0.494 | 0.426 | 0.588 | 0.976 | 0.444 | 0.734 |
| paper | 174 | 0.742 | 0.525 | 0.409 | 0.607 | 0.986 | 0.472 | 0.759 |

## Error taxonomy (§23; 370 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 327 | 0.88 | 76 |
| node hallucination | 197 | 0.53 | 47 |
| label corruption | 139 | 0.38 | 68 |
| wrong edge | 758 | 2.05 | 199 |
| missing edge | 810 | 2.19 | 166 |
| reversed edge | 263 | 0.71 | 94 |
| branch confusion | 367 | 0.99 | 185 |
| merge confusion | 480 | 1.30 | 207 |
| edge label loss | 693 | 1.87 | 122 |
| grouping failure | 803 | 2.17 | 141 |
| spurious edge | 753 | 2.04 | 167 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 42972 · median 31870 · p90 102631 · p95 106567 · max 119785

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `None`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.7, top_p 0.8, max_new_tokens 2048, seed 2; image max side 896
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-04 18:24 UTC, completed 2026-10-05 00:23 UTC
