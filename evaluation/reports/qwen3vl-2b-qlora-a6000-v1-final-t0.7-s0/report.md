# Evaluation run `qwen3vl-2b-qlora-a6000-v1-final-t0.7-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 470 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.870 | 0.273 | 500 |
| Edge F1 | 0.639 | 0.350 | 500 |
| Edge F1 (strict) | 0.615 | 0.361 | 500 |
| Graph similarity | 0.749 | 0.288 | 500 |
| Label accuracy | 0.980 | 0.079 | 467 |
| Structural QA | 0.582 | 0.359 | 500 |
| Diagram type | 0.910 | 0.286 | 500 |
| Valid (first attempt) | 0.726 | 0.446 | 500 |
| Valid (bare JSON) | 0.726 | 0.446 | 500 |
| Valid (post-repair) | 0.940 | 0.238 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.875 | 0.727 | 0.794 | 6411 | 913 | 2409 |
| Edges | 0.524 | 0.428 | 0.471 | 3804 | 3458 | 5085 |
| Edges (strict) | 0.503 | 0.411 | 0.452 | 3652 | 3610 | 5237 |

## Labels, edge text, grouping (matched items only)

- Labels (6411 matched): exact 0.975, case-insensitive 0.975, similarity 0.995, CER 0.005, WER 0.016
- Edge text (432 labeled edges matched): accuracy 0.539; lost 140, wrong 59, hallucinated 18
- Grouping (6411 matched nodes): accuracy 0.822; flattened 881, wrongly nested 94, wrong group 163

## Output validity (§20.2)

- Status: valid_first_attempt 363, repaired 87, failed 30, valid_after_retry 20 · mean attempts 1.27 · with repairs 87 · truncated outputs 1
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.680, edge F1 0.510, graph similarity 0.591

## Structural QA (§20.7): 0.566 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.598 |
| predecessors | 500 | 0.606 |
| sources | 500 | 0.536 |
| sinks | 500 | 0.500 |
| path_exists | 1000 | 0.754 |
| count_nodes | 500 | 0.624 |
| count_edges | 500 | 0.460 |
| group_members | 239 | 0.264 |
| merge_point | 356 | 0.343 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 1.000 | 0.899 | 0.877 | 0.950 | 1.000 | 0.905 | 1.000 |
| 2 | 125 | 0.990 | 0.829 | 0.797 | 0.905 | 0.999 | 0.776 | 1.000 |
| 3 | 125 | 0.937 | 0.604 | 0.570 | 0.762 | 0.992 | 0.467 | 0.984 |
| 4 | 125 | 0.554 | 0.224 | 0.215 | 0.381 | 0.912 | 0.182 | 0.776 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.886 | 0.687 | 0.687 | 0.786 | 0.959 | 0.618 | 0.986 |
| flowchart | 72 | 0.875 | 0.646 | 0.646 | 0.759 | 0.966 | 0.598 | 0.958 |
| ml_pipeline | 72 | 0.866 | 0.646 | 0.646 | 0.753 | 0.979 | 0.599 | 0.958 |
| neural_network | 72 | 0.879 | 0.680 | 0.680 | 0.777 | 0.982 | 0.599 | 0.958 |
| scientific_workflow | 72 | 0.870 | 0.696 | 0.696 | 0.780 | 0.990 | 0.641 | 0.931 |
| system_architecture | 72 | 0.882 | 0.680 | 0.630 | 0.764 | 0.991 | 0.647 | 0.931 |
| uml | 68 | 0.832 | 0.427 | 0.300 | 0.620 | 0.994 | 0.363 | 0.853 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.953 | 0.819 | 0.797 | 0.882 | 0.997 | 0.804 | 0.958 |
| layered_tb | 325 | 0.837 | 0.613 | 0.593 | 0.718 | 0.970 | 0.532 | 0.938 |
| radial | 103 | 0.916 | 0.594 | 0.556 | 0.755 | 0.998 | 0.587 | 0.932 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.856 | 0.626 | 0.600 | 0.735 | 0.978 | 0.572 | 0.929 |
| dark | 158 | 0.871 | 0.639 | 0.618 | 0.750 | 0.983 | 0.590 | 0.937 |
| paper | 174 | 0.884 | 0.652 | 0.626 | 0.763 | 0.978 | 0.586 | 0.954 |

## Error taxonomy (§23; 470 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 1319 | 2.81 | 184 |
| node hallucination | 913 | 1.94 | 133 |
| label corruption | 161 | 0.34 | 78 |
| wrong edge | 1606 | 3.42 | 264 |
| missing edge | 2066 | 4.40 | 241 |
| reversed edge | 298 | 0.63 | 130 |
| branch confusion | 642 | 1.37 | 252 |
| merge confusion | 757 | 1.61 | 271 |
| edge label loss | 217 | 0.46 | 106 |
| grouping failure | 1138 | 2.42 | 156 |
| spurious edge | 1554 | 3.31 | 211 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 37237 · median 24149 · p90 90722 · p95 107690 · max 176336

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.7, top_p 0.8, max_new_tokens 2048, seed 0; image max side 896
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-03 14:12 UTC, completed 2026-10-03 19:23 UTC
