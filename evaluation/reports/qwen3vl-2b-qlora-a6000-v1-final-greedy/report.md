# Evaluation run `qwen3vl-2b-qlora-a6000-v1-final-greedy`

- Predictor: `vlm:hf` · model `Qwen/Qwen3-VL-2B-Instruct` · adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Data: `synthetic-v1` split `test` · 500 of 500 samples · split hash `88ae7d751259`
- Graph produced for 455 samples; predictor errors: 0

## Headline (mean over samples; failures count as 0)

| Metric | Mean | Std | n |
| --- | --- | --- | --- |
| Node F1 | 0.854 | 0.302 | 500 |
| Edge F1 | 0.638 | 0.355 | 500 |
| Edge F1 (strict) | 0.611 | 0.364 | 500 |
| Graph similarity | 0.740 | 0.305 | 500 |
| Label accuracy | 0.984 | 0.064 | 454 |
| Structural QA | 0.582 | 0.365 | 500 |
| Diagram type | 0.882 | 0.323 | 500 |
| Valid (first attempt) | 0.728 | 0.445 | 500 |
| Valid (bare JSON) | 0.728 | 0.445 | 500 |
| Valid (post-repair) | 0.910 | 0.286 | 500 |

## Pooled over all nodes / edges (micro)

| | Precision | Recall | F1 | TP | FP | FN |
| --- | --- | --- | --- | --- | --- | --- |
| Nodes | 0.902 | 0.695 | 0.785 | 6131 | 667 | 2689 |
| Edges | 0.548 | 0.416 | 0.473 | 3702 | 3049 | 5187 |
| Edges (strict) | 0.527 | 0.400 | 0.455 | 3560 | 3191 | 5329 |

## Labels, edge text, grouping (matched items only)

- Labels (6131 matched): exact 0.978, case-insensitive 0.979, similarity 0.996, CER 0.004, WER 0.014
- Edge text (421 labeled edges matched): accuracy 0.542; lost 138, wrong 55, hallucinated 14
- Grouping (6131 matched nodes): accuracy 0.856; flattened 631, wrongly nested 99, wrong group 154

## Output validity (§20.2)

- Status: valid_first_attempt 364, repaired 65, failed 45, valid_after_retry 26 · mean attempts 1.27 · with repairs 65 · truncated outputs 0
- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 0.696, edge F1 0.534, graph similarity 0.610

## Structural QA (§20.7): 0.566 over 4595 questions

| Kind | Questions | Accuracy |
| --- | --- | --- |
| successors | 500 | 0.590 |
| predecessors | 500 | 0.586 |
| sources | 500 | 0.558 |
| sinks | 500 | 0.526 |
| path_exists | 1000 | 0.739 |
| count_nodes | 500 | 0.616 |
| count_edges | 500 | 0.442 |
| group_members | 239 | 0.314 |
| merge_point | 356 | 0.354 |

## By level

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 125 | 1.000 | 0.930 | 0.898 | 0.961 | 1.000 | 0.924 | 1.000 |
| 2 | 125 | 0.988 | 0.817 | 0.778 | 0.897 | 0.999 | 0.765 | 1.000 |
| 3 | 125 | 0.926 | 0.598 | 0.567 | 0.754 | 0.994 | 0.477 | 0.968 |
| 4 | 125 | 0.503 | 0.208 | 0.201 | 0.349 | 0.922 | 0.163 | 0.672 |

## By diagram type

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| data_pipeline | 72 | 0.859 | 0.692 | 0.692 | 0.775 | 0.988 | 0.603 | 0.944 |
| flowchart | 72 | 0.857 | 0.633 | 0.633 | 0.743 | 0.973 | 0.609 | 0.917 |
| ml_pipeline | 72 | 0.857 | 0.659 | 0.659 | 0.754 | 0.975 | 0.607 | 0.944 |
| neural_network | 72 | 0.874 | 0.668 | 0.668 | 0.769 | 0.975 | 0.603 | 0.944 |
| scientific_workflow | 72 | 0.894 | 0.703 | 0.703 | 0.795 | 0.989 | 0.648 | 0.944 |
| system_architecture | 72 | 0.864 | 0.694 | 0.639 | 0.762 | 0.993 | 0.662 | 0.889 |
| uml | 68 | 0.771 | 0.406 | 0.266 | 0.574 | 0.997 | 0.329 | 0.779 |

## By layout

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| circular | 72 | 0.941 | 0.828 | 0.800 | 0.878 | 0.998 | 0.803 | 0.944 |
| layered_tb | 325 | 0.824 | 0.609 | 0.586 | 0.709 | 0.975 | 0.530 | 0.905 |
| radial | 103 | 0.890 | 0.599 | 0.559 | 0.742 | 1.000 | 0.592 | 0.903 |

## By theme

| Value | n | Node F1 | Edge F1 | Strict | Graph sim. | Labels | QA | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blueprint | 168 | 0.832 | 0.634 | 0.604 | 0.725 | 0.978 | 0.582 | 0.905 |
| dark | 158 | 0.857 | 0.627 | 0.600 | 0.736 | 0.988 | 0.578 | 0.905 |
| paper | 174 | 0.874 | 0.652 | 0.628 | 0.758 | 0.985 | 0.586 | 0.920 |

## Error taxonomy (§23; 455 samples with a graph)

| Type | Total | Per sample | Samples affected |
| --- | --- | --- | --- |
| node omission | 1056 | 2.32 | 174 |
| node hallucination | 667 | 1.47 | 106 |
| label corruption | 134 | 0.29 | 71 |
| wrong edge | 1533 | 3.37 | 241 |
| missing edge | 1697 | 3.73 | 239 |
| reversed edge | 296 | 0.65 | 123 |
| branch confusion | 612 | 1.35 | 244 |
| merge confusion | 720 | 1.58 | 262 |
| edge label loss | 207 | 0.45 | 99 |
| grouping failure | 884 | 1.94 | 141 |
| spurious edge | 1220 | 2.68 | 190 |

## Latency per sample (ms, whole pipeline incl. retries)

mean 35537 · median 22382 · p90 85460 · p95 102475 · max 139985

## Reproducibility (§18.1)

- Model: backend `hf`, id `Qwen/Qwen3-VL-2B-Instruct`, revision `89644892e4d85e24eaac8bacfd4f463576704203`, adapter `E:\Asif\vigraph\output\runs\qwen3vl-2b-qlora-a6000-v1\adapter`
- Prompts: `graph_extraction@1` (d7097c8ad971), `graph_correction@1` (e0f443ebad7d)
- Decoding: temperature 0.0, top_p 1.0, max_new_tokens 2048, seed 0; image max side 896
- Adapter: base_model_name_or_path Qwen/Qwen3-VL-2B-Instruct, peft_type LORA, r 16, lora_alpha 32, lora_dropout 0.05, target_modules ['v_proj', 'k_proj', 'up_proj', 'o_proj', 'down_proj', 'gate_proj', 'q_proj']
- Versions: app 0.1.0, schema 2.0, matching 1, scores 1, qa_benchmark 1
- Split `test` hash `88ae7d751259f2eaa2fd612bb0aa2ad0e84c5ca57a06c029214031223309b6e3`; ground truth `8d4d2c69624c1a414c4c1d7073d3443736f5bb1e75e3abca2d1241a7989d6515`
- Started 2026-10-03 01:26 UTC, completed 2026-10-03 06:23 UTC
