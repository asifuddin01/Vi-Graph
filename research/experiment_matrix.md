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
| A-B | Image resolution 640 / 768 / 896 / 1024 (evaluation only, QLoRA) | §24B  | 640 / 768 / 1024 measured (below); 896 to re-run on the same GPU |
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

**Resolution ablation (§24B, evaluation only)** — the QLoRA adapter (trained at 896 px)
evaluated with `image_max_side` 640 / 768 / 1024 on the same 112 samples, greedy, 2048
tokens (runs `qwen3vl-2b-qlora-a6000-v1-px{640,768,1024}-s0`; comparisons in
`evaluation/reports/comparisons/qwen3vl-2b-qlora-a6000-v1-resolution/`; 18/18 files
sha256-verified, every sample re-scored here, identical). `image_max_side` caps the longest
side; smaller images are never enlarged (at 640 px, 105 of the 112 images are shrunk; at 1024,
81; every L4 image is shrunk at 640–896 and 27 of 28 at 1024).

**Hardware caveat.** These three runs ran on an **RTX 4080 SUPER**; the 896 px run is section 7's
**RTX A6000** run (same OS, PyTorch 2.11 / transformers 5.17). Greedy decoding is not
bit-identical across the two GPUs: on the 21 samples whose input image is identical in the
A6000 896 px and 4080 1024 px runs (never shrunk at either size), 3 first attempts differ
(L1–L2, diverging after 40–800 characters), while on one GPU the outputs are identical (13 of 13
and 7 of 7 such samples across the 4080 runs). Long L4 outputs are more exposed. So 896 px is
**not** directly comparable with the other three sizes; the hand-back's `px*-vs-px896`
comparisons are cross-GPU and kept only for the record. An 896 px run on the 4080 is pending
(the notebook now reuses a run only from the same GPU, and the runner refuses to resume a run
on a different GPU).

| Size    | GPU         | Node F1 | Edge F1 | Strict | Graph sim. | Labels | Struct. QA | Valid @1 | Valid (post-repair) | L4 runaways (stuck in nodes) | L4 failed |
| ------- | ----------- | ------- | ------- | ------ | ---------- | ------ | ---------- | -------- | ------------------- | ---------------------------- | --------- |
| 640 px  | 4080 SUPER  | 0.784   | 0.581   | 0.556  | 0.677      | 0.989  | 0.538      | 0.714    | 0.812               | 20 (19)                      | 20        |
| 768 px  | 4080 SUPER  | 0.823   | 0.626   | 0.608  | 0.720      | 0.980  | 0.572      | 0.688    | 0.875               | 14 (12)                      | 12        |
| 896 px  | A6000       | 0.844   | 0.624   | 0.591  | 0.727      | 0.985  | 0.564      | 0.670    | 0.893               | 11 (9)                       | 10        |
| 1024 px | 4080 SUPER  | 0.855   | 0.659   | 0.627  | 0.749      | 0.991  | 0.590      | 0.670    | 0.884               | 13 (10)                      | 12        |

Same-GPU paired tests (bootstrap, Holm across the 9 metrics; `*-same-gpu.md`):

- **1024 vs 640 px** — better structure: edge F1 +0.078 [+0.044, +0.116] (p_Holm 0.001),
  strict +0.071 (0.002), graph similarity +0.072 [+0.032, +0.114] (0.007), QA +0.052 (0.005);
  node F1 +0.071 (0.059, n.s. after Holm).
- **768 vs 640 px** — strict edge F1 +0.051 (p_Holm 0.03); edge F1 +0.046 and graph similarity
  +0.043 (n.s. after Holm).
- **1024 vs 768 px** — all differences positive for structure (+0.03) but none significant on
  112 samples.

By level (4080 runs, 640 → 768 → 1024), the gain is in the dense diagrams: graph similarity L3
0.705 → 0.732 → 0.778 and L4 0.154 → 0.273 → 0.372 (edge F1 L4 0.075 → 0.148 → 0.261), while
L1–L2 stay flat (L1 0.968 / 0.980 / 0.969, L2 0.881 / 0.895 / 0.876). Label accuracy on matched
nodes barely moves (0.980–0.991): lower resolution costs structure, not label reading.

**Runaways vs resolution.** At 640 px, 20 of 28 L4 first attempts run away (19 stuck in the node
list); from 768 px up it stays at about half (14 at 768, 13 at 1024). The runaway set is unstable:
only 7 L4 diagrams run away at all three 4080 sizes, 23 at one size or another, and 5 never.
Within L4, the runaways are not the larger images (median original longest side, runaway vs
finished: 1648 vs 1889 px at 640, 1840 vs 1574 at 768, 1536 vs 1858 at 1024), so the weak
downscale association seen earlier does not hold up. Too little resolution makes runaways more
frequent, but above 768 px resolution is not their main cause: the next candidates are on the
decoding side (a logged runaway guard) and in training (more long L4 targets).

**Hypotheses so far** (synthetic test subset only; one run per condition):
H1 (fine-tuning helps) — supported. H2 (edges degrade faster than nodes with complexity) —
consistent for all three systems. H6 (VLM beats the classical baseline) — **not supported yet**
on structure: fine-tuned ≈ baseline on node/edge/graph similarity, better on labels, QA and
diagram type; zero-shot is below the baseline. The token budget is ruled out as the L4 confound
(above); L4 failures are runaway enumeration. H3 (small text / dense layouts hurt labels and
edges most) — partly supported by the resolution ablation: lower resolution hurts edges on
dense diagrams, but not label accuracy on matched nodes. Open before drawing conclusions: seed
variance (§20.10), the full 500-sample test, and the real-diagram set (§15). Runs must be compared
on the same GPU.
