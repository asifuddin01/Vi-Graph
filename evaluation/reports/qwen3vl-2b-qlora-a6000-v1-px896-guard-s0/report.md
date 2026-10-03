# Evaluation run `qwen3vl-2b-qlora-a6000-v1-px896-guard-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 101 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.853 | 0.305 | 112 |
| Edge F1 | 0.637 | 0.361 | 112 |
| Edge F1 (strict) | 0.600 | 0.368 | 112 |
| Graph similarity | 0.736 | 0.306 | 112 |
| Label accuracy | 0.991 | 0.035 | 101 |
| Structural QA | 0.570 | 0.371 | 112 |
| Diagram type | 0.866 | 0.342 | 112 |
| Valid (first attempt) | 0.661 | 0.476 | 112 |
| Valid (bare JSON) | 0.661 | 0.476 | 112 |
| Valid (post-repair) | 0.902 | 0.299 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.928 | 0.695 | 0.795 | 1359 | 105 | 596 |
| Edges | 0.564 | 0.422 | 0.483 | 823 | 635 | 1128 |
| Edges (strict) | 0.540 | 0.403 | 0.462 | 787 | 671 | 1164 |

## Labels, edge text, grouping (matched items only)

- Labels (1359 matched): exact 0.985, case-insensitive 0.987, similarity 0.997, CER 0.003, WER 0.011
- Edge text (89 labeled edges matched): accuracy 0.494; lost 30, wrong 15, hallucinated 2
- Grouping (1359 matched nodes): accuracy 0.851; flattened 154, wrongly nested 19, wrong group 30

## Output validity (§20.2)

- Status: valid_first_attempt 74, repaired 19, failed 11, valid_after_retry 8 · mean attempts 1.34 · with repairs 19 · truncated outputs 0
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.637, edge F1 0.502, graph similarity 0.562

## Structural QA (§20.7): 0.553 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.562 |
| predecessors | 112 | 0.589 |
| sources | 112 | 0.527 |
| sinks | 112 | 0.545 |
| path_exists | 224 | 0.719 |
| count_nodes | 112 | 0.625 |
| count_edges | 112 | 0.393 |
| group_members | 56 | 0.339 |
| merge_point | 78 | 0.346 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 1.000 | 0.977 | 0.905 | 0.972 | 1.000 | 0.964 | 1.000 |
| 2 | 28 | 0.990 | 0.758 | 0.711 | 0.868 | 1.000 | 0.695 | 1.000 |
| 3 | 28 | 0.923 | 0.614 | 0.588 | 0.761 | 0.996 | 0.480 | 0.964 |
| 4 | 28 | 0.501 | 0.199 | 0.195 | 0.344 | 0.953 | 0.141 | 0.643 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.846 | 0.583 | 0.583 | 0.715 | 0.995 | 0.521 | 0.938 |
| flowchart | 16 | 0.808 | 0.572 | 0.572 | 0.686 | 0.968 | 0.585 | 0.875 |
| ml_pipeline | 16 | 0.855 | 0.704 | 0.704 | 0.776 | 0.989 | 0.605 | 0.938 |
| neural_network | 16 | 0.849 | 0.648 | 0.648 | 0.745 | 0.995 | 0.598 | 0.875 |
| scientific_workflow | 16 | 0.975 | 0.779 | 0.779 | 0.874 | 0.993 | 0.674 | 1.000 |
| system_architecture | 16 | 0.900 | 0.749 | 0.665 | 0.804 | 0.993 | 0.669 | 0.938 |
| uml | 16 | 0.741 | 0.428 | 0.249 | 0.554 | 1.000 | 0.339 | 0.750 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.867 | 0.729 | 0.646 | 0.775 | 1.000 | 0.693 | 0.867 |
| layered_tb | 71 | 0.828 | 0.614 | 0.592 | 0.716 | 0.985 | 0.510 | 0.901 |
| radial | 26 | 0.914 | 0.647 | 0.593 | 0.770 | 1.000 | 0.664 | 0.923 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.859 | 0.669 | 0.613 | 0.749 | 0.994 | 0.593 | 0.886 |
| dark | 33 | 0.825 | 0.618 | 0.584 | 0.711 | 0.995 | 0.556 | 0.879 |
| paper | 44 | 0.870 | 0.627 | 0.601 | 0.746 | 0.985 | 0.562 | 0.932 |

## Error taxonomy (§23; 101 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 197 | 1.95 | 36 |
| node hallucination | 105 | 1.04 | 22 |
| label corruption | 20 | 0.20 | 13 |
| wrong edge | 349 | 3.46 | 53 |
| missing edge | 329 | 3.26 | 54 |
| reversed edge | 58 | 0.57 | 24 |
| branch confusion | 144 | 1.43 | 54 |
| merge confusion | 167 | 1.65 | 59 |
| edge label loss | 47 | 0.47 | 25 |
| grouping failure | 203 | 2.01 | 30 |
| spurious edge | 228 | 2.26 | 43 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 38100 · median 23301 · p90 94367 · p95 98246 · max 109381

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 2048, seed 0; image max side 896
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-02 19:40 UTC, completed 2026-10-02 20:52 UTC
