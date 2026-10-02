# Evaluation run `qwen3vl-2b-qlora-a6000-v1-px1024-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 99 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.855 | 0.318 | 112 |
| Edge F1 | 0.659 | 0.355 | 112 |
| Edge F1 (strict) | 0.627 | 0.364 | 112 |
| Graph similarity | 0.749 | 0.311 | 112 |
| Label accuracy | 0.991 | 0.027 | 99 |
| Structural QA | 0.590 | 0.366 | 112 |
| Diagram type | 0.875 | 0.332 | 112 |
| Valid (first attempt) | 0.670 | 0.472 | 112 |
| Valid (bare JSON) | 0.670 | 0.472 | 112 |
| Valid (post-repair) | 0.884 | 0.322 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.961 | 0.699 | 0.809 | 1367 | 56 | 588 |
| Edges | 0.632 | 0.453 | 0.528 | 884 | 515 | 1067 |
| Edges (strict) | 0.613 | 0.439 | 0.512 | 857 | 542 | 1094 |

## Labels, edge text, grouping (matched items only)

- Labels (1367 matched): exact 0.984, case-insensitive 0.984, similarity 0.996, CER 0.003, WER 0.010
- Edge text (103 labeled edges matched): accuracy 0.563; lost 27, wrong 18, hallucinated 4
- Grouping (1367 matched nodes): accuracy 0.841; flattened 164, wrongly nested 17, wrong group 36

## Output validity (§20.2)

- Status: valid_first_attempt 75, repaired 17, failed 13, valid_after_retry 7 · mean attempts 1.33 · with repairs 17 · truncated outputs 16
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.654, edge F1 0.513, graph similarity 0.577

## Structural QA (§20.7): 0.575 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.589 |
| predecessors | 112 | 0.625 |
| sources | 112 | 0.545 |
| sinks | 112 | 0.536 |
| path_exists | 224 | 0.741 |
| count_nodes | 112 | 0.652 |
| count_edges | 112 | 0.473 |
| group_members | 56 | 0.375 |
| merge_point | 78 | 0.282 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 1.000 | 0.972 | 0.899 | 0.969 | 1.000 | 0.948 | 1.000 |
| 2 | 28 | 0.990 | 0.768 | 0.740 | 0.876 | 1.000 | 0.720 | 1.000 |
| 3 | 28 | 0.933 | 0.634 | 0.611 | 0.778 | 0.994 | 0.522 | 0.964 |
| 4 | 28 | 0.495 | 0.261 | 0.258 | 0.372 | 0.958 | 0.169 | 0.571 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.890 | 0.619 | 0.619 | 0.754 | 0.989 | 0.572 | 0.938 |
| flowchart | 16 | 0.886 | 0.664 | 0.664 | 0.772 | 0.979 | 0.649 | 0.938 |
| ml_pipeline | 16 | 0.881 | 0.723 | 0.723 | 0.800 | 0.996 | 0.629 | 0.938 |
| neural_network | 16 | 0.859 | 0.664 | 0.664 | 0.758 | 0.988 | 0.598 | 0.875 |
| scientific_workflow | 16 | 0.982 | 0.814 | 0.814 | 0.896 | 0.998 | 0.731 | 1.000 |
| system_architecture | 16 | 0.800 | 0.687 | 0.621 | 0.728 | 0.995 | 0.631 | 0.812 |
| uml | 16 | 0.683 | 0.441 | 0.284 | 0.535 | 0.996 | 0.319 | 0.688 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.931 | 0.745 | 0.659 | 0.815 | 0.997 | 0.708 | 0.933 |
| layered_tb | 71 | 0.815 | 0.636 | 0.620 | 0.721 | 0.987 | 0.539 | 0.859 |
| radial | 26 | 0.917 | 0.672 | 0.627 | 0.787 | 1.000 | 0.660 | 0.923 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.840 | 0.651 | 0.609 | 0.734 | 0.995 | 0.589 | 0.857 |
| dark | 33 | 0.845 | 0.669 | 0.640 | 0.747 | 0.993 | 0.617 | 0.879 |
| paper | 44 | 0.873 | 0.658 | 0.632 | 0.762 | 0.987 | 0.570 | 0.909 |

## Error taxonomy (§23; 99 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 125 | 1.26 | 31 |
| node hallucination | 56 | 0.57 | 17 |
| label corruption | 22 | 0.22 | 12 |
| wrong edge | 311 | 3.14 | 52 |
| missing edge | 246 | 2.48 | 49 |
| reversed edge | 60 | 0.61 | 24 |
| branch confusion | 134 | 1.35 | 55 |
| merge confusion | 164 | 1.66 | 56 |
| edge label loss | 49 | 0.49 | 25 |
| grouping failure | 217 | 2.19 | 29 |
| spurious edge | 144 | 1.45 | 39 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 49227 · median 21587 · p90 177431 · p95 181421 · max 209386

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 2048, seed 0; image max side 1024
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-01 21:15 UTC, completed 2026-10-01 22:47 UTC
