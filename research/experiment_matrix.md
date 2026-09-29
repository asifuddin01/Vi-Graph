# Experiment matrix

Planned experiments. Results are recorded only once measured, with full run metadata
(spec §18.1) stored in `evaluation/reports/`.

All conditions: identical evaluation protocol for every row (VLM or not), 3+ seeds per
condition, mean ± std (§20.10), paired significance test for comparisons (§20.11).

## Models (§19)

| ID       | Model                             | Status      |
| -------- | --------------------------------- | ----------- |
| Baseline | OCR + rule-based geometry (§19.1) — `evaluation/baseline/` v1 | evaluated (synthetic test) |
| A        | Compact VLM (tentative: Qwen3-VL-2B-Instruct) | not started |
| B        | Another compact VLM               | not chosen  |
| C        | Medium VLM                        | not chosen  |
| D        | Larger VLM, if resources permit   | not chosen  |

## Experiments

| ID  | Experiment                                              | Spec  | Status      |
| --- | ------------------------------------------------------- | ----- | ----------- |
| E1  | Complexity robustness: all models × difficulty L1–L4    | §21   | not started |
| E2  | Image perturbation: blur, compression, low-res, small text, occlusion, crowding | §22 | not started |
| A-A | Zero-shot vs. QLoRA fine-tuned                          | §24A  | not started |
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
