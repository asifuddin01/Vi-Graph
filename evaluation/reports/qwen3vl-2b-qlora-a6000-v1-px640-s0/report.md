# Evaluation run `qwen3vl-2b-qlora-a6000-v1-px640-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 91 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.784 | 0.384 | 112 |
| Edge F1 | 0.581 | 0.401 | 112 |
| Edge F1 (strict) | 0.556 | 0.400 | 112 |
| Graph similarity | 0.677 | 0.365 | 112 |
| Label accuracy | 0.989 | 0.040 | 91 |
| Structural QA | 0.538 | 0.392 | 112 |
| Diagram type | 0.804 | 0.399 | 112 |
| Valid (first attempt) | 0.714 | 0.454 | 112 |
| Valid (bare JSON) | 0.714 | 0.454 | 112 |
| Valid (post-repair) | 0.812 | 0.392 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.953 | 0.566 | 0.710 | 1106 | 55 | 849 |
| Edges | 0.564 | 0.325 | 0.413 | 635 | 491 | 1316 |
| Edges (strict) | 0.546 | 0.315 | 0.400 | 615 | 511 | 1336 |

## Labels, edge text, grouping (matched items only)

- Labels (1106 matched): exact 0.979, case-insensitive 0.979, similarity 0.995, CER 0.005, WER 0.014
- Edge text (59 labeled edges matched): accuracy 0.390; lost 21, wrong 15, hallucinated 0
- Grouping (1106 matched nodes): accuracy 0.902; flattened 64, wrongly nested 6, wrong group 38

## Output validity (§20.2)

- Status: valid_first_attempt 80, failed 21, repaired 10, valid_after_retry 1 · mean attempts 1.29 · with repairs 10 · truncated outputs 21
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.690, edge F1 0.513, graph similarity 0.597

## Structural QA (§20.7): 0.518 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.518 |
| predecessors | 112 | 0.536 |
| sources | 112 | 0.500 |
| sinks | 112 | 0.482 |
| path_exists | 224 | 0.670 |
| count_nodes | 112 | 0.607 |
| count_edges | 112 | 0.420 |
| group_members | 56 | 0.321 |
| merge_point | 78 | 0.295 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 1.000 | 0.960 | 0.908 | 0.968 | 1.000 | 0.956 | 1.000 |
| 2 | 28 | 0.992 | 0.775 | 0.745 | 0.881 | 1.000 | 0.728 | 1.000 |
| 3 | 28 | 0.904 | 0.512 | 0.498 | 0.705 | 0.980 | 0.398 | 0.964 |
| 4 | 28 | 0.239 | 0.075 | 0.074 | 0.154 | 0.937 | 0.069 | 0.286 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.746 | 0.528 | 0.528 | 0.637 | 0.996 | 0.522 | 0.750 |
| flowchart | 16 | 0.778 | 0.525 | 0.525 | 0.648 | 0.981 | 0.579 | 0.812 |
| ml_pipeline | 16 | 0.771 | 0.649 | 0.649 | 0.708 | 0.993 | 0.586 | 0.812 |
| neural_network | 16 | 0.715 | 0.573 | 0.573 | 0.643 | 0.972 | 0.499 | 0.750 |
| scientific_workflow | 16 | 0.907 | 0.730 | 0.730 | 0.818 | 0.992 | 0.635 | 0.938 |
| system_architecture | 16 | 0.839 | 0.670 | 0.601 | 0.738 | 0.990 | 0.616 | 0.875 |
| uml | 16 | 0.731 | 0.387 | 0.285 | 0.548 | 0.996 | 0.326 | 0.750 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.867 | 0.698 | 0.664 | 0.773 | 1.000 | 0.679 | 0.867 |
| layered_tb | 71 | 0.706 | 0.528 | 0.515 | 0.614 | 0.981 | 0.463 | 0.746 |
| radial | 26 | 0.947 | 0.655 | 0.607 | 0.793 | 0.998 | 0.660 | 0.962 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.827 | 0.616 | 0.574 | 0.713 | 0.993 | 0.586 | 0.857 |
| dark | 33 | 0.753 | 0.560 | 0.546 | 0.651 | 0.989 | 0.495 | 0.788 |
| paper | 44 | 0.772 | 0.568 | 0.549 | 0.668 | 0.985 | 0.531 | 0.795 |

## Error taxonomy (§23; 91 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 105 | 1.15 | 30 |
| node hallucination | 55 | 0.60 | 15 |
| label corruption | 23 | 0.25 | 12 |
| wrong edge | 284 | 3.12 | 46 |
| missing edge | 214 | 2.35 | 47 |
| reversed edge | 57 | 0.63 | 20 |
| branch confusion | 113 | 1.24 | 45 |
| merge confusion | 134 | 1.47 | 48 |
| edge label loss | 36 | 0.40 | 18 |
| grouping failure | 108 | 1.19 | 19 |
| spurious edge | 150 | 1.65 | 36 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 53549 · median 19847 · p90 182403 · p95 185535 · max 205934

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 2048, seed 0; image max side 640
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-01 18:00 UTC, completed 2026-10-01 19:40 UTC
