# Evaluation run `qwen3vl-2b-qlora-a6000-v1-final-t0.7-s2`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 466 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.861 | 0.285 | 500 |
| Edge F1 | 0.635 | 0.354 | 500 |
| Edge F1 (strict) | 0.608 | 0.363 | 500 |
| Graph similarity | 0.742 | 0.296 | 500 |
| Label accuracy | 0.981 | 0.071 | 461 |
| Structural QA | 0.585 | 0.362 | 500 |
| Diagram type | 0.904 | 0.295 | 500 |
| Valid (first attempt) | 0.722 | 0.448 | 500 |
| Valid (bare JSON) | 0.722 | 0.448 | 500 |
| Valid (post-repair) | 0.932 | 0.252 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.868 | 0.710 | 0.781 | 6264 | 951 | 2556 |
| Edges | 0.516 | 0.414 | 0.459 | 3678 | 3446 | 5211 |
| Edges (strict) | 0.495 | 0.397 | 0.441 | 3529 | 3595 | 5360 |

## Labels, edge text, grouping (matched items only)

- Labels (6264 matched): exact 0.973, case-insensitive 0.974, similarity 0.995, CER 0.005, WER 0.017
- Edge text (424 labeled edges matched): accuracy 0.538; lost 135, wrong 61, hallucinated 17
- Grouping (6264 matched nodes): accuracy 0.827; flattened 819, wrongly nested 81, wrong group 186

## Output validity (§20.2)

- Status: valid_first_attempt 361, repaired 75, failed 34, valid_after_retry 30 · mean attempts 1.28 · with repairs 75 · truncated outputs 4
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.678, edge F1 0.516, graph similarity 0.592

## Structural QA (§20.7): 0.568 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.600 |
| predecessors | 500 | 0.592 |
| sources | 500 | 0.566 |
| sinks | 500 | 0.516 |
| path_exists | 1000 | 0.752 |
| count_nodes | 500 | 0.610 |
| count_edges | 500 | 0.452 |
| group_members | 239 | 0.276 |
| merge_point | 356 | 0.343 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 1.000 | 0.916 | 0.890 | 0.956 | 1.000 | 0.910 | 1.000 |
| 2 | 125 | 0.990 | 0.837 | 0.792 | 0.907 | 0.999 | 0.796 | 1.000 |
| 3 | 125 | 0.923 | 0.579 | 0.549 | 0.743 | 0.993 | 0.462 | 0.976 |
| 4 | 125 | 0.532 | 0.207 | 0.199 | 0.363 | 0.912 | 0.171 | 0.752 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.864 | 0.688 | 0.688 | 0.774 | 0.981 | 0.602 | 0.958 |
| flowchart | 72 | 0.886 | 0.638 | 0.638 | 0.761 | 0.976 | 0.612 | 0.958 |
| ml_pipeline | 72 | 0.871 | 0.645 | 0.645 | 0.754 | 0.981 | 0.594 | 0.958 |
| neural_network | 72 | 0.874 | 0.671 | 0.671 | 0.770 | 0.970 | 0.612 | 0.972 |
| scientific_workflow | 72 | 0.873 | 0.688 | 0.688 | 0.778 | 0.974 | 0.629 | 0.958 |
| system_architecture | 72 | 0.875 | 0.674 | 0.624 | 0.759 | 0.990 | 0.664 | 0.917 |
| uml | 68 | 0.781 | 0.427 | 0.281 | 0.590 | 0.997 | 0.369 | 0.794 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.941 | 0.830 | 0.801 | 0.880 | 0.998 | 0.807 | 0.944 |
| layered_tb | 325 | 0.828 | 0.597 | 0.575 | 0.705 | 0.971 | 0.530 | 0.932 |
| radial | 103 | 0.910 | 0.616 | 0.576 | 0.762 | 1.000 | 0.602 | 0.922 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.851 | 0.616 | 0.590 | 0.728 | 0.968 | 0.572 | 0.935 |
| dark | 158 | 0.851 | 0.623 | 0.594 | 0.731 | 0.989 | 0.583 | 0.899 |
| paper | 174 | 0.881 | 0.663 | 0.636 | 0.766 | 0.985 | 0.599 | 0.960 |

## Error taxonomy (§23; 466 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 1335 | 2.86 | 177 |
| node hallucination | 951 | 2.04 | 121 |
| label corruption | 166 | 0.36 | 81 |
| wrong edge | 1635 | 3.51 | 250 |
| missing edge | 2084 | 4.47 | 246 |
| reversed edge | 266 | 0.57 | 121 |
| branch confusion | 634 | 1.36 | 250 |
| merge confusion | 745 | 1.60 | 270 |
| edge label loss | 213 | 0.46 | 104 |
| grouping failure | 1086 | 2.33 | 150 |
| spurious edge | 1545 | 3.32 | 202 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 38378 · median 24193 · p90 98000 · p95 111583 · max 188187

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.7, top_p 0.8, max_new_tokens 2048, seed 2; image max side 896
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-04 13:04 UTC, completed 2026-10-04 18:24 UTC
