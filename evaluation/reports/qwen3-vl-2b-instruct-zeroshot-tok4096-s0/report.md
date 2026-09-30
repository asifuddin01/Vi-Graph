# Evaluation run `qwen3-vl-2b-instruct-zeroshot-tok4096-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 85 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.736 | 0.422 | 112 |
| Edge F1 | 0.502 | 0.397 | 112 |
| Edge F1 (strict) | 0.432 | 0.384 | 112 |
| Graph similarity | 0.601 | 0.373 | 112 |
| Label accuracy | 0.971 | 0.071 | 85 |
| Structural QA | 0.454 | 0.372 | 112 |
| Diagram type | 0.339 | 0.476 | 112 |
| Valid (first attempt) | 0.536 | 0.501 | 112 |
| Valid (bare JSON) | 0.000 | 0.000 | 112 |
| Valid (post-repair) | 0.759 | 0.430 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.939 | 0.512 | 0.662 | 1000 | 65 | 955 |
| Edges | 0.550 | 0.304 | 0.392 | 593 | 485 | 1358 |
| Edges (strict) | 0.483 | 0.267 | 0.344 | 521 | 557 | 1430 |

## Labels, edge text, grouping (matched items only)

- Labels (1000 matched): exact 0.945, case-insensitive 0.957, similarity 0.990, CER 0.009, WER 0.041
- Edge text (51 labeled edges matched): accuracy 0.490; lost 9, wrong 17, hallucinated 169
- Grouping (1000 matched nodes): accuracy 0.791; flattened 208, wrongly nested 1, wrong group 0

## Output validity (§20.2)

- Status: valid_first_attempt 60, failed 27, repaired 17, valid_after_retry 8 · mean attempts 1.46 · with repairs 17 · truncated outputs 27
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.521, edge F1 0.354, graph similarity 0.425

## Structural QA (§20.7): 0.437 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.464 |
| predecessors | 112 | 0.491 |
| sources | 112 | 0.446 |
| sinks | 112 | 0.366 |
| path_exists | 224 | 0.594 |
| count_nodes | 112 | 0.580 |
| count_edges | 112 | 0.357 |
| group_members | 56 | 0.018 |
| merge_point | 78 | 0.167 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 0.964 | 0.771 | 0.679 | 0.855 | 1.000 | 0.806 | 0.964 |
| 2 | 28 | 1.000 | 0.657 | 0.542 | 0.802 | 0.996 | 0.585 | 1.000 |
| 3 | 28 | 0.818 | 0.523 | 0.453 | 0.643 | 0.962 | 0.393 | 0.857 |
| 4 | 28 | 0.161 | 0.059 | 0.056 | 0.105 | 0.761 | 0.032 | 0.214 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.782 | 0.532 | 0.513 | 0.646 | 0.938 | 0.510 | 0.812 |
| flowchart | 16 | 0.681 | 0.326 | 0.316 | 0.503 | 0.975 | 0.412 | 0.688 |
| ml_pipeline | 16 | 0.738 | 0.595 | 0.563 | 0.657 | 0.972 | 0.442 | 0.750 |
| neural_network | 16 | 0.822 | 0.522 | 0.520 | 0.667 | 0.960 | 0.464 | 0.875 |
| scientific_workflow | 16 | 0.788 | 0.612 | 0.572 | 0.689 | 0.976 | 0.553 | 0.812 |
| system_architecture | 16 | 0.788 | 0.572 | 0.478 | 0.653 | 0.991 | 0.511 | 0.812 |
| uml | 16 | 0.551 | 0.358 | 0.065 | 0.393 | 0.995 | 0.286 | 0.562 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.855 | 0.626 | 0.544 | 0.714 | 0.996 | 0.574 | 0.867 |
| layered_tb | 71 | 0.684 | 0.517 | 0.436 | 0.577 | 0.955 | 0.426 | 0.718 |
| radial | 26 | 0.808 | 0.390 | 0.357 | 0.602 | 0.995 | 0.461 | 0.808 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.719 | 0.458 | 0.393 | 0.576 | 0.977 | 0.435 | 0.743 |
| dark | 33 | 0.700 | 0.479 | 0.458 | 0.578 | 0.968 | 0.421 | 0.727 |
| paper | 44 | 0.777 | 0.555 | 0.445 | 0.639 | 0.969 | 0.494 | 0.795 |

## Error taxonomy (§23; 85 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 87 | 1.02 | 20 |
| node hallucination | 65 | 0.76 | 12 |
| label corruption | 55 | 0.65 | 19 |
| wrong edge | 213 | 2.51 | 50 |
| missing edge | 209 | 2.46 | 41 |
| reversed edge | 63 | 0.74 | 20 |
| branch confusion | 98 | 1.15 | 46 |
| merge confusion | 125 | 1.47 | 51 |
| edge label loss | 195 | 2.29 | 31 |
| grouping failure | 209 | 2.46 | 37 |
| spurious edge | 209 | 2.46 | 40 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 141935 · median 57012 · p90 449299 · p95 468750 · max 480815

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `None`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 4096, seed 0; image max side 896
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-09-30 12:03 UTC, completed 2026-09-30 16:29 UTC
