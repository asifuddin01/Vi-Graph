# Evaluation

Scores reconstructed graphs against ground truth (spec §20) with full run metadata (§18.1).
Everything builds on the locked node/edge matching in `metrics/matching.py` (§20.1).

| Path                        | Contents                                                        |
| --------------------------- | --------------------------------------------------------------- |
| `metrics/matching.py`       | §20.1 node/edge matching — matching v1 (locked)                 |
| `metrics/scores.py`         | Per-sample scores v1: validity, P/R/F1, graph similarity, labels, edge text, grouping, diagram type |
| `metrics/errors.py`         | Automatic §23 error taxonomy counts                            |
| `metrics/structural_qa.py`  | Structural QA benchmark v1 (§20.7)                              |
| `samples.py`                | Load + verify a dataset split (hashes)                          |
| `predictors.py`             | VLM pipeline predictor; oracle sanity check                     |
| `baseline/`                 | Classical non-VLM baseline: OCR + geometry (§19.1)              |
| `runner.py`, `aggregate.py`, `report.py` | Resumable runs, summaries, markdown reports        |
| `stats.py`, `compare.py`    | Variance over seeds (§20.10), paired significance tests (§20.11) |
| `scripts/runaway_report.py` | Why outputs hit max_new_tokens, per level (runaway enumeration) |
| `reports/<run>/`            | One directory per run                                           |

Every definition is in the module docstrings, pinned by a version constant
(`MATCHING_VERSION`, `SCORES_VERSION`, `QA_BENCHMARK_VERSION`) that is logged with each run.

## Running

From the repo root, with `backend/` on `PYTHONPATH`:

```bash
# Sanity check of the whole evaluation path: every score must be 1.000.
PYTHONPATH=backend python -m evaluation run --dataset data/synthetic/synthetic-v1 \
    --split test --backend oracle --out /tmp/oracle

# A real model (needs requirements-vlm.txt and a GPU; float16 on a T4).
PYTHONPATH=backend python -m evaluation run --dataset data/synthetic/synthetic-v1 \
    --split test --backend hf --dtype float16 --image-max-side 1024 \
    --out evaluation/reports/qwen3vl-2b-zeroshot-s0

# With a LoRA adapter trained in Colab.
PYTHONPATH=backend python -m evaluation run ... --adapter path/to/adapter --out ...

# Rewrite summary/report; re-score stored predictions after a scoring version bump.
PYTHONPATH=backend python -m evaluation summarize evaluation/reports/<run>
PYTHONPATH=backend python -m evaluation rescore evaluation/reports/<run>
```

`--limit N` evaluates the first N samples of the split; splits are ordered so any prefix
of 28 covers every level × diagram type. Decoding is greedy by default; `--temperature`,
`--top-p` and `--seed` set sampling for run-to-run variance (§20.10).

**Resuming:** each sample is appended to `predictions.jsonl` and fsynced as soon as it is
scored. Re-running the same command on the same `--out` continues where it stopped (a
different config, or a rebuilt split with a different hash, is refused). Samples whose
predictor raised (e.g. CUDA out of memory) count as failures; `--retry-errors` re-runs
them. Three errors in a row stop the run.

## Outputs (`--out` directory)

| File                  | Contents                                                        | Committed |
| --------------------- | --------------------------------------------------------------- | --------- |
| `run.json`            | Config, split + hashes, §18.1 metadata (model + revision, adapter + LoRA config, prompt ids/hashes, decoding, seed, schema), versions, git commit, packages, GPU | yes |
| `predictions.jsonl`   | Per sample: every raw model output, repairs, normalization, final and first-attempt graphs, scores, QA outcomes | no (large) |
| `predictions.jsonl.gz`| The same, compressed (~20×)                                     | yes       |
| `summary.json`        | Aggregates: macro (mean ± std, n) and pooled metrics, validity, QA by kind, taxonomy, latency, breakdowns by level / diagram type / layout / theme | yes |
| `report.md`           | The summary as tables                                           | yes       |

Headline numbers are means over samples in which failed predictions score 0 (so validity
failures are never hidden); pooled numbers sum counts over the run first.

## Across runs: variance and significance

```bash
# Run-to-run variance (§20.10): runs of one condition that differ only in --seed.
PYTHONPATH=backend python -m evaluation seeds evaluation/reports/zeroshot-s{0,1,2} \
    --out evaluation/reports/zeroshot-seeds.md

# Paired comparison (§20.11): condition A vs B, each one run or several seeds.
PYTHONPATH=backend python -m evaluation compare \
    --a evaluation/reports/zeroshot-s{0,1,2} --b evaluation/reports/qlora-s{0,1,2} \
    --out evaluation/reports/qlora-vs-zeroshot.md
```

`seeds` reports each metric as mean ± std of the per-run means, overall and per difficulty
level (the §21 complexity curves). It refuses runs that differ in anything but the seed.

`compare` pairs the conditions per test sample (a condition's value for a sample is the
mean over its runs) and reports, per metric: both means, Δ = B − A, a 95% bootstrap CI,
and p-values. **Primary test: paired bootstrap** over test samples (10,000 resamples,
two-sided, null-centered); Holm–Bonferroni adjusted across the metrics compared. The paired
t-test and Wilcoxon signed-rank test are shown for reference. Both commands require the
same split build (split hash) and the same samples in every run. With greedy decoding,
seeds only change the result through GPU nondeterminism; use sampling (`--temperature`)
when measuring decoding variance.

## Non-VLM baseline (§19.1)

`evaluation/baseline/` reconstructs graphs with Tesseract OCR and OpenCV geometry, no VLM,
so the VLM rows of the §19.1 table have a classical reference scored by the identical
protocol. Install `requirements-baseline.txt` and the Tesseract binary
(`apt-get install tesseract-ocr`), then:

```bash
PYTHONPATH=backend python -m evaluation run --dataset data/synthetic/synthetic-v1 \
    --split test --backend baseline --out evaluation/reports/baseline-v1
```

How it works (details in `baseline/pipeline.py`): *ink* = thin structures (pixels far from
their local median), so light, dark and colour-filled themes binarize alike; *nodes* =
enclosed regions with ink inside; *filled groups* = painted areas enclosing shapes;
*labels* = Tesseract per shape on a cleaned crop; *edges* = strokes left after removing
shapes and text, directed by comparing the ink at each end (arrowhead vs bare line);
free text next to a stroke becomes that edge's label. Types come from shape (diamond →
decision, hexagon → fusion) and position (sources → input, sinks → output); every edge is
`flows_to`; diagram type is a keyword vote.

It is generic — it knows nothing about the generator's themes, fonts or vocabularies — and
its two tuned constants were set on the **val** split only. Known v1 limitations: dashed
group borders (not closed shapes), labels touching or crossed by strokes, text below
~6 px, UML relation types.
