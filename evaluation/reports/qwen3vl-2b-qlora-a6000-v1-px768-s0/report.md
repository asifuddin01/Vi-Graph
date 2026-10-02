# Evaluation run `qwen3vl-2b-qlora-a6000-v1-px768-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 98 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.823 | 0.345 | 112 |
| Edge F1 | 0.626 | 0.376 | 112 |
| Edge F1 (strict) | 0.608 | 0.375 | 112 |
| Graph similarity | 0.720 | 0.338 | 112 |
| Label accuracy | 0.980 | 0.080 | 97 |
| Structural QA | 0.572 | 0.379 | 112 |
| Diagram type | 0.857 | 0.351 | 112 |
| Valid (first attempt) | 0.688 | 0.466 | 112 |
| Valid (bare JSON) | 0.688 | 0.466 | 112 |
| Valid (post-repair) | 0.875 | 0.332 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.900 | 0.639 | 0.747 | 1249 | 139 | 706 |
| Edges | 0.556 | 0.384 | 0.454 | 749 | 598 | 1202 |
| Edges (strict) | 0.543 | 0.375 | 0.443 | 731 | 616 | 1220 |

## Labels, edge text, grouping (matched items only)

- Labels (1249 matched): exact 0.975, case-insensitive 0.976, similarity 0.995, CER 0.005, WER 0.016
- Edge text (67 labeled edges matched): accuracy 0.552; lost 21, wrong 9, hallucinated 2
- Grouping (1249 matched nodes): accuracy 0.849; flattened 155, wrongly nested 8, wrong group 25

## Output validity (§20.2)

- Status: valid_first_attempt 77, repaired 14, failed 14, valid_after_retry 7 · mean attempts 1.31 · with repairs 14 · truncated outputs 17
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.660, edge F1 0.516, graph similarity 0.584

## Structural QA (§20.7): 0.553 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.589 |
| predecessors | 112 | 0.571 |
| sources | 112 | 0.518 |
| sinks | 112 | 0.518 |
| path_exists | 224 | 0.719 |
| count_nodes | 112 | 0.634 |
| count_edges | 112 | 0.446 |
| group_members | 56 | 0.339 |
| merge_point | 78 | 0.295 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 1.000 | 0.967 | 0.951 | 0.980 | 1.000 | 0.956 | 1.000 |
| 2 | 28 | 0.992 | 0.812 | 0.770 | 0.895 | 1.000 | 0.744 | 1.000 |
| 3 | 28 | 0.892 | 0.579 | 0.564 | 0.732 | 0.991 | 0.468 | 0.929 |
| 4 | 28 | 0.407 | 0.148 | 0.146 | 0.273 | 0.889 | 0.120 | 0.571 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.839 | 0.608 | 0.608 | 0.721 | 0.981 | 0.576 | 0.938 |
| flowchart | 16 | 0.790 | 0.551 | 0.551 | 0.669 | 0.934 | 0.540 | 0.875 |
| ml_pipeline | 16 | 0.797 | 0.667 | 0.667 | 0.730 | 0.981 | 0.607 | 0.875 |
| neural_network | 16 | 0.881 | 0.650 | 0.650 | 0.761 | 0.988 | 0.585 | 0.938 |
| scientific_workflow | 16 | 0.966 | 0.768 | 0.768 | 0.865 | 0.985 | 0.674 | 1.000 |
| system_architecture | 16 | 0.805 | 0.691 | 0.667 | 0.740 | 1.000 | 0.674 | 0.812 |
| uml | 16 | 0.681 | 0.452 | 0.344 | 0.554 | 1.000 | 0.348 | 0.688 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.867 | 0.729 | 0.701 | 0.789 | 1.000 | 0.686 | 0.867 |
| layered_tb | 71 | 0.781 | 0.580 | 0.563 | 0.676 | 0.970 | 0.506 | 0.859 |
| radial | 26 | 0.912 | 0.695 | 0.676 | 0.802 | 0.997 | 0.685 | 0.923 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.797 | 0.644 | 0.617 | 0.712 | 0.993 | 0.600 | 0.857 |
| dark | 33 | 0.796 | 0.591 | 0.591 | 0.691 | 0.964 | 0.543 | 0.848 |
| paper | 44 | 0.863 | 0.639 | 0.612 | 0.748 | 0.983 | 0.572 | 0.909 |

## Error taxonomy (§23; 98 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 217 | 2.21 | 35 |
| node hallucination | 139 | 1.42 | 21 |
| label corruption | 31 | 0.32 | 14 |
| wrong edge | 287 | 2.93 | 49 |
| missing edge | 376 | 3.84 | 53 |
| reversed edge | 62 | 0.63 | 29 |
| branch confusion | 119 | 1.21 | 50 |
| merge confusion | 149 | 1.52 | 54 |
| edge label loss | 32 | 0.33 | 16 |
| grouping failure | 188 | 1.92 | 26 |
| spurious edge | 249 | 2.54 | 44 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 50559 · median 23522 · p90 180611 · p95 189459 · max 208860

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 2048, seed 0; image max side 768
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-01 19:40 UTC, completed 2026-10-01 21:15 UTC
