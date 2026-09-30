# Evaluation run `qwen3vl-2b-qlora-a6000-v1-tok4096-s0`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `F:\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 112 of 500 samples · split hash `88ae7d751259`
- Graph produced for 100 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.844 | 0.319 | 112 |
| Edge F1 | 0.624 | 0.367 | 112 |
| Edge F1 (strict) | 0.591 | 0.370 | 112 |
| Graph similarity | 0.727 | 0.316 | 112 |
| Label accuracy | 0.985 | 0.054 | 100 |
| Structural QA | 0.562 | 0.378 | 112 |
| Diagram type | 0.866 | 0.342 | 112 |
| Valid (first attempt) | 0.670 | 0.472 | 112 |
| Valid (bare JSON) | 0.670 | 0.472 | 112 |
| Valid (post-repair) | 0.893 | 0.311 | 112 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.921 | 0.678 | 0.781 | 1326 | 114 | 629 |
| Edges | 0.552 | 0.404 | 0.467 | 788 | 639 | 1163 |
| Edges (strict) | 0.528 | 0.386 | 0.446 | 753 | 674 | 1198 |

## Labels, edge text, grouping (matched items only)

- Labels (1326 matched): exact 0.982, case-insensitive 0.983, similarity 0.996, CER 0.004, WER 0.013
- Edge text (81 labeled edges matched): accuracy 0.519; lost 24, wrong 15, hallucinated 1
- Grouping (1326 matched nodes): accuracy 0.871; flattened 130, wrongly nested 15, wrong group 26

## Output validity (§20.2)

- Status: valid_first_attempt 75, repaired 18, failed 12, valid_after_retry 7 · mean attempts 1.33 · with repairs 18 · truncated outputs 14
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.641, edge F1 0.495, graph similarity 0.562

## Structural QA (§20.7): 0.546 over 1030 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 112 | 0.545 |
| predecessors | 112 | 0.580 |
| sources | 112 | 0.518 |
| sinks | 112 | 0.545 |
| path_exists | 224 | 0.692 |
| count_nodes | 112 | 0.625 |
| count_edges | 112 | 0.429 |
| group_members | 56 | 0.321 |
| merge_point | 78 | 0.333 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 28 | 1.000 | 0.936 | 0.890 | 0.959 | 1.000 | 0.942 | 1.000 |
| 2 | 28 | 0.990 | 0.779 | 0.729 | 0.878 | 1.000 | 0.695 | 1.000 |
| 3 | 28 | 0.900 | 0.609 | 0.583 | 0.747 | 0.996 | 0.483 | 0.929 |
| 4 | 28 | 0.486 | 0.171 | 0.161 | 0.323 | 0.924 | 0.128 | 0.643 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 16 | 0.823 | 0.561 | 0.561 | 0.692 | 0.961 | 0.527 | 0.938 |
| flowchart | 16 | 0.802 | 0.527 | 0.527 | 0.664 | 0.965 | 0.537 | 0.875 |
| ml_pipeline | 16 | 0.866 | 0.696 | 0.696 | 0.778 | 0.986 | 0.597 | 0.938 |
| neural_network | 16 | 0.847 | 0.650 | 0.650 | 0.745 | 0.995 | 0.598 | 0.875 |
| scientific_workflow | 16 | 0.913 | 0.750 | 0.750 | 0.829 | 0.995 | 0.674 | 0.938 |
| system_architecture | 16 | 0.858 | 0.741 | 0.649 | 0.776 | 0.996 | 0.650 | 0.875 |
| uml | 16 | 0.799 | 0.439 | 0.301 | 0.602 | 1.000 | 0.353 | 0.812 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 15 | 0.867 | 0.716 | 0.683 | 0.782 | 1.000 | 0.678 | 0.867 |
| layered_tb | 71 | 0.800 | 0.599 | 0.575 | 0.692 | 0.976 | 0.506 | 0.873 |
| radial | 26 | 0.953 | 0.637 | 0.581 | 0.789 | 1.000 | 0.650 | 0.962 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 35 | 0.873 | 0.633 | 0.579 | 0.741 | 0.984 | 0.584 | 0.914 |
| dark | 33 | 0.786 | 0.602 | 0.589 | 0.687 | 0.995 | 0.549 | 0.818 |
| paper | 44 | 0.865 | 0.632 | 0.602 | 0.744 | 0.979 | 0.555 | 0.932 |

## Error taxonomy (§23; 100 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 197 | 1.97 | 34 |
| node hallucination | 114 | 1.14 | 21 |
| label corruption | 24 | 0.24 | 13 |
| wrong edge | 337 | 3.37 | 54 |
| missing edge | 326 | 3.26 | 53 |
| reversed edge | 73 | 0.73 | 30 |
| branch confusion | 139 | 1.39 | 52 |
| merge confusion | 165 | 1.65 | 59 |
| edge label loss | 40 | 0.40 | 19 |
| grouping failure | 171 | 1.71 | 28 |
| spurious edge | 229 | 2.29 | 41 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 121786 · median 34878 · p90 590849 · p95 640331 · max 951986

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `F:\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 4096, seed 0; image max side 896
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-09-30 08:14 UTC, completed 2026-09-30 12:02 UTC
