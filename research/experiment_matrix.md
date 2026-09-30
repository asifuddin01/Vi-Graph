# Experiment matrix

Planned experiments. Results are recorded only once measured, with full run metadata
(spec §18.1) stored in `evaluation/reports/`.

All conditions: identical evaluation protocol for every row (VLM or not), 3+ seeds per
condition, mean ± std (§20.10), paired significance test for comparisons (§20.11).

## Models (§19)

| ID       | Model                             | Status      |
| -------- | --------------------------------- | ----------- |
| Baseline | OCR + rule-based geometry (§19.1) — `evaluation/baseline/` v1 | evaluated (synthetic test) |
| A        | Compact VLM: Qwen3-VL-2B-Instruct                      | zero-shot + QLoRA evaluated (112-sample test subset, 2048 + 4096 tokens) |
| B        | Another compact VLM               | not chosen  |
| C        | Medium VLM                        | not chosen  |
| D        | Larger VLM, if resources permit   | not chosen  |

## Experiments

| ID  | Experiment                                              | Spec  | Status      |
| --- | ------------------------------------------------------- | ----- | ----------- |
| E1  | Complexity robustness: all models × difficulty L1–L4    | §21   | not started |
| E2  | Image perturbation: blur, compression, low-res, small text, occlusion, crowding | §22 | not started |
| A-A | Zero-shot vs. QLoRA fine-tuned                          | §24A  | first run measured (below) |
| A-B | Image resolution 512 / 768 / 1024                       | §24B  | not started |
| A-C | Prompt variants: simple / structured / + constraints    | §24C  | not started |
| A-D | Raw VLM output vs. validated/normalized/repaired output | §24D  | not started |
| A-E | Synthetic-only vs. synthetic + real training data       | §24E  | not started |
| A-F | VLM vs. non-VLM baseline                                | §24F  | not started |

## Hypotheses under test (§25)

H1 fine-tuning helps validity/accuracy · H2 edges degrade faster than nodes with
complexity · H3 small text/dense layouts hurt labels and edges most · H4 validation/repair
reduces invalid predictions · H5 synthetic → real transfer · H6 VLM beats the classical
baseline, with the gap widening as complexity grows.

## Measured results

All on synthetic-v1 **test** (500 samples; held-out layouts layered_tb / radial / circular
and themes dark / blueprint / paper; split hash `2c67f24b3b83…`). Macro means over
samples, failures count as 0. Single deterministic run (the baseline has no sampling, so
seeds do not apply).

| Model                  | Node F1 | Edge F1 | Edge F1 strict | Graph sim. | Labels | Struct. QA | Report |
| ---------------------- | ------- | ------- | -------------- | ---------- | ------ | ---------- | ------ |
| Baseline v1 (OCR + CV) | 0.931   | 0.635   | 0.584          | 0.781      | 0.960  | 0.462      | [`baseline-v1`](../evaluation/reports/baseline-v1/report.md) |

Baseline by level (L1 → L4): edge F1 0.697 / 0.646 / 0.647 / 0.552; structural QA 0.670 /
0.505 / 0.378 / 0.295. Weakest: radial layouts (edge F1 0.344), edge text (accuracy 0.031
— labels are mostly lost), UML relation types (strict edge F1 0.000: it only emits
flows_to), groups with dashed borders (1,224 matched nodes flattened).

### Model A: zero-shot vs QLoRA vs baseline (run `qwen3vl-2b-qlora-a6000-v1`)

**Training** (`training/runs/qwen3vl-2b-qlora-a6000-v1/`): Qwen3-VL-2B-Instruct (revision
`8964489`), 4-bit NF4 QLoRA, r=16/α=32 on the language model's attention + MLP projections
(17.4 M trainable of 2.14 B parameters), bf16, 2 epochs over the 2,000 training diagrams
(250 optimizer steps, lr 1e-4 cosine), image_max_side 896. One RTX A6000 with PyTorch capped at
10.5 GB: **peak 7.6 GB allocated during training** (9.3 GB peak reserved on the three longest
sequences, memory probe) — **1.4 h** end to end. Train loss 0.478 → 0.069; validation loss
0.147 → 0.066 (48 val samples), flat after step ~200.

**Evaluation**: synthetic-v1 **test**, the stratified 112-sample prefix (4 × every level ×
diagram type), on the Windows data build (Graphviz 16.1, split hash `88ae7d75…`; ground truth
byte-identical to the committed build). Greedy decoding, max_new_tokens 2048, image_max_side
896, one run per condition — no seed variance yet. All three runs were re-scored here from their
stored predictions and reproduce exactly.

| Condition                | Node F1 | Edge F1 | Strict | Graph sim. | Labels | Struct. QA | Diagram type | Valid @1 | Valid (post-repair) |
| ------------------------ | ------- | ------- | ------ | ---------- | ------ | ---------- | ------------ | -------- | ------------------- |
| Baseline v1 (OCR + CV)   | 0.865   | 0.620   | 0.569  | 0.736      | 0.878  | 0.447      | 0.732        | –        | 1.000               |
| Qwen3-VL-2B zero-shot    | 0.712   | 0.497   | 0.420  | 0.586      | 0.984  | 0.451      | 0.321        | 0.509    | 0.723               |
| Qwen3-VL-2B QLoRA        | 0.844   | 0.624   | 0.591  | 0.727      | 0.985  | 0.564      | 0.866        | 0.670    | 0.893               |

Paired tests (bootstrap, Holm-adjusted; `evaluation/reports/comparisons/qwen3vl-2b-qlora-a6000-v1/`):

- **QLoRA vs zero-shot** — better on every metric, all significant: node F1 +0.132
  [+0.066, +0.200], edge F1 +0.127 [+0.082, +0.178], strict edge F1 +0.171, graph similarity
  +0.140 [+0.095, +0.187], QA +0.113, diagram type +0.545, first-attempt validity +0.161,
  post-repair validity +0.170 (p_Holm ≤ 0.02).
- **QLoRA vs baseline** — structure not significantly different (node F1 −0.021 [−0.072,
  +0.025], edge F1 +0.004, graph similarity −0.009); better labels (+0.080), QA (+0.117),
  diagram type (+0.134); lower post-repair validity (−0.107: the baseline always emits a graph).
- **Zero-shot vs baseline** — the baseline is better on structure (node F1 +0.153, edge F1
  +0.124, graph similarity +0.150); QA equal.

By level (node F1 / edge F1 / QA):

| Level | Baseline            | Zero-shot           | QLoRA               |
| ----- | ------------------- | ------------------- | ------------------- |
| L1    | 0.988 / 0.859 / 0.809 | 1.000 / 0.787 / 0.813 | 1.000 / 0.936 / 0.942 |
| L2    | 0.916 / 0.627 / 0.470 | 1.000 / 0.657 / 0.585 | 0.990 / 0.779 / 0.695 |
| L3    | 0.942 / 0.675 / 0.357 | 0.819 / 0.526 / 0.402 | 0.900 / 0.611 / 0.490 |
| L4    | 0.614 / 0.321 / 0.152 | 0.028 / 0.016 / 0.004 | 0.486 / 0.171 / 0.128 |

**Re-evaluation with max_new_tokens 4096** (Phase 7 step 1; runs `*-tok4096-s0`, same
112 samples, everything else unchanged; comparisons in
`evaluation/reports/comparisons/qwen3vl-2b-qlora-a6000-v1-tok4096/`; re-scored here, identical).
At 2048 tokens, zero-shot outputs were truncated on 27 of 28 L4 diagrams and the fine-tuned
model's on 11 of 28, so the budget looked like a confound. **It is not:**

| Condition                   | Node F1 | Edge F1 | Strict | Graph sim. | Labels | Struct. QA | Valid @1 | Valid (post-repair) | L4 truncated |
| --------------------------- | ------- | ------- | ------ | ---------- | ------ | ---------- | -------- | ------------------- | ------------ |
| Zero-shot, 2048 tokens      | 0.712   | 0.497   | 0.420  | 0.586      | 0.984  | 0.451      | 0.509    | 0.723               | 27 / 28      |
| Zero-shot, 4096 tokens      | 0.736   | 0.502   | 0.432  | 0.601      | 0.971  | 0.454      | 0.536    | 0.759               | 22 / 28      |
| QLoRA, 2048 tokens          | 0.844   | 0.624   | 0.591  | 0.727      | 0.985  | 0.564      | 0.670    | 0.893               | 11 / 28      |
| QLoRA, 4096 tokens          | 0.844   | 0.624   | 0.591  | 0.727      | 0.985  | 0.562      | 0.670    | 0.893               | 11 / 28      |

- **QLoRA: no change.** The same 14 first attempts hit the limit at 2048 and at 4096 (the
  other 98 are byte-identical). The only score difference is one L3 sample (`test-000102`)
  whose retry saw the longer truncated attempt (QA −0.002, n.s.).
- **Zero-shot: small gain.** L4 truncations 27 → 22, node F1 +0.024, graph similarity +0.015;
  L4 node F1 0.028 → 0.161, still far below QLoRA (0.486) and the baseline (0.614).
- **Conclusions unchanged at 4096**: QLoRA vs zero-shot is still better on every metric, all
  significant (node F1 +0.108, edge F1 +0.121, strict +0.158, graph similarity +0.125, QA
  +0.108, diagram type +0.527, validity @1 +0.134, post-repair +0.134; p_Holm ≤ 0.031); QLoRA
  vs baseline still n.s. on structure; zero-shot still below the baseline on structure (node
  F1 −0.129, edge F1 −0.118, graph similarity −0.135; QA +0.007, n.s.).

**Why L4 outputs don't finish: runaway enumeration.** Each truncated first attempt is
classified from its raw text by `evaluation/scripts/runaway_report.py` (tested on these
runs). At L4 the model either never reaches the `"edges"` list, because it keeps listing
nodes, mostly invented ones, or it emits far more edges than the diagram has:

| Run (L4, 28 samples)   | Truncated | Stuck in nodes | Repeating edges | Excess edges (> 2× GT) | Other | Failed |
| ---------------------- | --------- | -------------- | --------------- | ---------------------- | ----- | ------ |
| Zero-shot, 2048        | 27        | 19             | 0               | 0                      | 8     | 27     |
| Zero-shot, 4096        | 22        | 19             | 2               | 1                      | 0     | 22     |
| QLoRA, 2048 and 4096   | 11        | 9              | 0               | 2                      | 0     | 10     |

Examples: 161 invented node ids for a 43-node diagram, "Logger" repeated 246 times, 205
edges for a 23-edge diagram. More tokens only lengthen the loop. Candidate causes, not yet
tested: image resolution, since L4 images are downscaled more (median ×1.96 for runaways vs
×1.80 for finished L4 outputs, a weak association that reverses for zero-shot at L3; §24B
will test it), and the lack of a stopping signal at generation time (a runaway guard or
salvage in Stage C is a possible fix, and it would have to be logged as a repair). Runaways
also dominate evaluation time: QLoRA at 4096 tokens took a median of 35 s per sample but a mean
of 122 s and up to 16 min, 3.8 h for the 112 samples.

**Hypotheses so far** (synthetic test subset only; one run per condition):
H1 (fine-tuning helps) — supported. H2 (edges degrade faster than nodes with complexity) —
consistent for all three systems. H6 (VLM beats the classical baseline) — **not supported yet**
on structure: fine-tuned ≈ baseline on node/edge/graph similarity, better on labels, QA and
diagram type; zero-shot is below the baseline. The token budget is ruled out as the L4 confound
(above); L4 failures are runaway enumeration. Open before drawing conclusions: seed variance
(§20.10), the full 500-sample test, and the real-diagram set (§15).
