# Evaluation run `qwen3vl-2b-qlora-a6000-v1-final-t0.7-s1`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 470 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.874 | 0.270 | 500 |
| Edge F1 | 0.642 | 0.350 | 500 |
| Edge F1 (strict) | 0.620 | 0.361 | 500 |
| Graph similarity | 0.754 | 0.285 | 500 |
| Label accuracy | 0.978 | 0.077 | 467 |
| Structural QA | 0.576 | 0.365 | 500 |
| Diagram type | 0.912 | 0.284 | 500 |
| Valid (first attempt) | 0.706 | 0.456 | 500 |
| Valid (bare JSON) | 0.706 | 0.456 | 500 |
| Valid (post-repair) | 0.940 | 0.238 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.889 | 0.735 | 0.805 | 6482 | 809 | 2338 |
| Edges | 0.527 | 0.426 | 0.472 | 3791 | 3399 | 5098 |
| Edges (strict) | 0.508 | 0.411 | 0.454 | 3649 | 3541 | 5240 |

## Labels, edge text, grouping (matched items only)

- Labels (6482 matched): exact 0.973, case-insensitive 0.973, similarity 0.995, CER 0.006, WER 0.018
- Edge text (445 labeled edges matched): accuracy 0.546; lost 140, wrong 62, hallucinated 22
- Grouping (6482 matched nodes): accuracy 0.842; flattened 786, wrongly nested 113, wrong group 127

## Output validity (§20.2)

- Status: valid_first_attempt 353, repaired 89, failed 30, valid_after_retry 28 · mean attempts 1.29 · with repairs 89 · truncated outputs 0
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.671, edge F1 0.511, graph similarity 0.588

## Structural QA (§20.7): 0.558 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.584 |
| predecessors | 500 | 0.572 |
| sources | 500 | 0.528 |
| sinks | 500 | 0.512 |
| path_exists | 1000 | 0.753 |
| count_nodes | 500 | 0.614 |
| count_edges | 500 | 0.448 |
| group_members | 239 | 0.272 |
| merge_point | 356 | 0.334 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 1.000 | 0.912 | 0.899 | 0.958 | 1.000 | 0.899 | 1.000 |
| 2 | 125 | 0.990 | 0.841 | 0.808 | 0.911 | 0.999 | 0.787 | 1.000 |
| 3 | 125 | 0.925 | 0.588 | 0.556 | 0.749 | 0.990 | 0.446 | 0.968 |
| 4 | 125 | 0.582 | 0.228 | 0.218 | 0.397 | 0.909 | 0.171 | 0.792 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.864 | 0.712 | 0.712 | 0.787 | 0.976 | 0.615 | 0.958 |
| flowchart | 72 | 0.881 | 0.651 | 0.651 | 0.764 | 0.967 | 0.614 | 0.958 |
| ml_pipeline | 72 | 0.871 | 0.665 | 0.665 | 0.764 | 0.985 | 0.606 | 0.944 |
| neural_network | 72 | 0.883 | 0.684 | 0.684 | 0.780 | 0.966 | 0.605 | 0.972 |
| scientific_workflow | 72 | 0.903 | 0.695 | 0.695 | 0.796 | 0.976 | 0.618 | 0.958 |
| system_architecture | 72 | 0.883 | 0.680 | 0.634 | 0.766 | 0.985 | 0.645 | 0.931 |
| uml | 68 | 0.833 | 0.393 | 0.280 | 0.611 | 0.994 | 0.312 | 0.853 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.941 | 0.821 | 0.810 | 0.880 | 0.997 | 0.794 | 0.944 |
| layered_tb | 325 | 0.840 | 0.607 | 0.588 | 0.717 | 0.967 | 0.520 | 0.935 |
| radial | 103 | 0.936 | 0.627 | 0.588 | 0.781 | 0.999 | 0.598 | 0.951 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.862 | 0.630 | 0.605 | 0.740 | 0.968 | 0.571 | 0.940 |
| dark | 158 | 0.863 | 0.625 | 0.604 | 0.740 | 0.982 | 0.573 | 0.918 |
| paper | 174 | 0.897 | 0.670 | 0.649 | 0.780 | 0.985 | 0.583 | 0.960 |

## Error taxonomy (§23; 470 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 1249 | 2.66 | 181 |
| node hallucination | 809 | 1.72 | 121 |
| label corruption | 178 | 0.38 | 89 |
| wrong edge | 1691 | 3.60 | 249 |
| missing edge | 1999 | 4.25 | 243 |
| reversed edge | 299 | 0.64 | 134 |
| branch confusion | 648 | 1.38 | 252 |
| merge confusion | 761 | 1.62 | 271 |
| edge label loss | 224 | 0.48 | 104 |
| grouping failure | 1026 | 2.18 | 150 |
| spurious edge | 1409 | 3.00 | 204 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 37759 · median 24505 · p90 94891 · p95 109937 · max 147496

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.7, top_p 0.8, max_new_tokens 2048, seed 1; image max side 896
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-04 01:28 UTC, completed 2026-10-04 06:43 UTC
