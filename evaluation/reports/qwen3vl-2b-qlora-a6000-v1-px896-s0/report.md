# Evaluation run `qwen3vl-2b-qlora-a6000-v1-px896-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 100 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.846 | 0.315 | 112 |
| Edge F1 | 0.633 | 0.369 | 112 |
| Edge F1 (strict) | 0.595 | 0.377 | 112 |
| Graph similarity | 0.730 | 0.314 | 112 |
| Label accuracy | 0.990 | 0.035 | 100 |
| Structural QA | 0.573 | 0.375 | 112 |
| Diagram type | 0.857 | 0.351 | 112 |
| Valid (first attempt) | 0.661 | 0.476 | 112 |
| Valid (bare JSON) | 0.661 | 0.476 | 112 |
| Valid (post-repair) | 0.893 | 0.311 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.933 | 0.683 | 0.789 | 1336 | 96 | 619 |
| Edges | 0.568 | 0.414 | 0.479 | 808 | 615 | 1143 |
| Edges (strict) | 0.543 | 0.396 | 0.458 | 772 | 651 | 1179 |

## Labels, edge text, grouping (matched items only)

- Labels (1336 matched): exact 0.985, case-insensitive 0.987, similarity 0.997, CER 0.004, WER 0.011
- Edge text (85 labeled edges matched): accuracy 0.506; lost 27, wrong 15, hallucinated 2
- Grouping (1336 matched nodes): accuracy 0.853; flattened 147, wrongly nested 19, wrong group 30

## Output validity (§20.2)

- Status: valid_first_attempt 74, repaired 19, failed 12, valid_after_retry 7 · mean attempts 1.34 · with repairs 19 · truncated outputs 15
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.637, edge F1 0.502, graph similarity 0.562

## Structural QA (§20.7): 0.556 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.562 |
| predecessors | 112 | 0.598 |
| sources | 112 | 0.536 |
| sinks | 112 | 0.562 |
| path_exists | 224 | 0.710 |
| count_nodes | 112 | 0.625 |
| count_edges | 112 | 0.402 |
| group_members | 56 | 0.339 |
| merge_point | 78 | 0.346 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 1.000 | 0.977 | 0.905 | 0.972 | 1.000 | 0.964 | 1.000 |
| 2 | 28 | 0.990 | 0.758 | 0.711 | 0.868 | 1.000 | 0.695 | 1.000 |
| 3 | 28 | 0.860 | 0.589 | 0.564 | 0.717 | 0.996 | 0.484 | 0.893 |
| 4 | 28 | 0.533 | 0.206 | 0.199 | 0.365 | 0.955 | 0.149 | 0.679 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.796 | 0.563 | 0.563 | 0.680 | 0.995 | 0.521 | 0.875 |
| flowchart | 16 | 0.808 | 0.572 | 0.572 | 0.686 | 0.968 | 0.585 | 0.875 |
| ml_pipeline | 16 | 0.855 | 0.704 | 0.704 | 0.776 | 0.989 | 0.605 | 0.938 |
| neural_network | 16 | 0.849 | 0.648 | 0.648 | 0.745 | 0.995 | 0.598 | 0.875 |
| scientific_workflow | 16 | 0.975 | 0.798 | 0.798 | 0.883 | 0.993 | 0.711 | 1.000 |
| system_architecture | 16 | 0.839 | 0.704 | 0.622 | 0.751 | 0.993 | 0.637 | 0.875 |
| uml | 16 | 0.797 | 0.439 | 0.256 | 0.591 | 1.000 | 0.353 | 0.812 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.867 | 0.729 | 0.646 | 0.775 | 1.000 | 0.693 | 0.867 |
| layered_tb | 71 | 0.803 | 0.604 | 0.583 | 0.698 | 0.985 | 0.511 | 0.873 |
| radial | 26 | 0.949 | 0.654 | 0.598 | 0.793 | 1.000 | 0.673 | 0.962 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.857 | 0.653 | 0.597 | 0.742 | 0.994 | 0.585 | 0.886 |
| dark | 33 | 0.802 | 0.617 | 0.583 | 0.698 | 0.994 | 0.572 | 0.848 |
| paper | 44 | 0.870 | 0.628 | 0.601 | 0.746 | 0.985 | 0.564 | 0.932 |

## Error taxonomy (§23; 100 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 199 | 1.99 | 36 |
| node hallucination | 96 | 0.96 | 20 |
| label corruption | 20 | 0.20 | 13 |
| wrong edge | 341 | 3.41 | 51 |
| missing edge | 327 | 3.27 | 52 |
| reversed edge | 58 | 0.58 | 24 |
| branch confusion | 141 | 1.41 | 52 |
| merge confusion | 161 | 1.61 | 57 |
| edge label loss | 44 | 0.44 | 23 |
| grouping failure | 196 | 1.96 | 29 |
| spurious edge | 216 | 2.16 | 41 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 51706 · median 24192 · p90 182670 · p95 188987 · max 194899

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 2048, seed 0; image max side 896
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-02 17:20 UTC, completed 2026-10-02 18:57 UTC
