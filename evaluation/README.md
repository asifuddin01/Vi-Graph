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
| `runner.py`, `aggregate.py`, `report.py` | Resumable runs, summaries, markdown reports        |
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
