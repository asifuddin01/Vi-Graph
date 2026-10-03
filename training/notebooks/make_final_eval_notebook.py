"""Generate vigraph_final_eval_windows.ipynb (Phase 7's final GPU run) from this script.

    python training/notebooks/make_final_eval_notebook.py

The notebook is standalone: its setup (settings aside) and dataset check are copied from the
Windows training notebook, vigraph_qlora_windows.ipynb, so a fix there reaches both. Then:
section A, greedy decoding on all 500 test samples (fine-tuned, zero-shot, OCR baseline), and
section B, three sampling seeds per model. The test suite checks that the committed notebook
matches this script.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = HERE / "vigraph_qlora_windows.ipynb"
NOTEBOOK = HERE / "vigraph_final_eval_windows.ipynb"
ROOT_DIR = r"E:\Asif\vigraph"  # where the user's main notebook, data, adapter and runs live


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n")}


def code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "source": text.strip("\n")}


def relocate(text: str) -> str:
    """The main notebook's folder (F:) → this machine's (prose, comments and messages only)."""
    return text.replace("F:\\\\vigraph", ROOT_DIR.replace("\\", "\\\\")).replace(
        "F:\\vigraph", ROOT_DIR
    )


def source_cells() -> list[dict]:
    return json.loads(SOURCE.read_text(encoding="utf-8"))["cells"]


def text_of(cell: dict) -> str:
    return "".join(cell["source"])


def setup_cells() -> list[dict]:
    """Section 1 (minus its settings) and the dataset check, from the main notebook."""
    cells = source_cells()
    start = next(i for i, c in enumerate(cells) if text_of(c).startswith("## 1. Setup"))
    end = next(
        i for i, c in enumerate(cells) if text_of(c).startswith('manifest_path = DATA_DIR / "')
    )
    chosen = []
    for cell in cells[start : end + 1]:
        text = text_of(cell)
        if text.startswith("# ---- Settings"):
            chosen.append(code(SETTINGS + "\n\n" + shared_settings(text)))
        elif text.startswith("## 2. Dataset"):
            chosen.append(md(DATASET_INTRO))
        else:
            chosen.append(
                {"cell_type": cell["cell_type"], "metadata": {}, "source": relocate(text)}
            )
    return chosen


def shared_settings(main_settings: str) -> str:
    """The Graphviz download and library pins, exactly as in the main notebook."""
    return main_settings[main_settings.index("# Portable Graphviz") :]


INTRO = r"""
# Vi-Graph — final evaluation (Phase 7, last GPU run)

The last GPU run of the project. It evaluates the trained adapter (`RUN_NAME`) and the
zero-shot model on the **whole held-out test split (500 diagrams)** with the settings chosen in
Phase 7 (896 px, 2048 tokens, runaway guard on), plus the OCR baseline:

| Section | What it does | Time (RTX 4080 SUPER, rough) |
| --- | --- | --- |
| 1. Setup | Settings, helpers, system check, latest code, libraries, GPU test (all quick when already installed) | ~2 min |
| 2. Dataset | Checks the dataset the main notebook built (rebuilds it only if missing) | ~1 min |
| A. Greedy, all 500 | Fine-tuned, zero-shot, OCR baseline; paired comparisons; hand-back zip | ~12–14 h |
| B. 3 sampling seeds per model | Run-to-run variance (§20.10): 3 seeds × 2 models; seed statistics; hand-back zip | ~35–45 h (all 500) or ~9 h (`SEED_LIMIT = 112`) |

**How to run it:** put this notebook in `E:\Asif\vigraph` next to the main notebook, open it,
**Select Kernel → `.venv`** (the same one), and run the cells in order. Every run is
resumable: after a stop or restart, run sections 1–2 and A.1 again, then the cell you were in.
Keep sleep set to *Never*.

**Send section A's zip as soon as A is done** (cell A.6), before starting B, so the write-up can
start while B runs. All runs must stay on this PC's GPU (the runner refuses to resume a run on a
different one).
"""

SETTINGS = rf"""
# ---- Settings (the same folder, run and adapter as the main notebook) --------------------
from pathlib import Path

ROOT = Path(r"{ROOT_DIR}")   # the main notebook's folder: repo, data, model cache, runs, results
REPO_URL = "https://github.com/asifuddin01/Vi-Graph.git"
BRANCH = "claude/tender-ramanujan-70dwgj"

VRAM_LIMIT_GB = 10.5             # PyTorch limit, as in the main notebook
RUN_NAME = "qwen3vl-2b-qlora-a6000-v1"   # the trained adapter: output\runs\<RUN_NAME>\adapter
COMPUTE_DTYPE = "bfloat16"
RUN_BASELINE = True              # OCR baseline on all 500 (CPU) — skipped if Tesseract is missing
DATA_WORKERS = 8                 # only used if the dataset has to be rebuilt

# ---- Final evaluation --------------------------------------------------------------------
IMAGE_MAX_SIDE = 896             # the adapter's training size; 768–1024 scored the same
MAX_NEW_TOKENS = 2048            # 4096 changed nothing
RUNAWAY_GUARD = True             # same scores, 26 % less time
SEEDS = [0, 1, 2]                # section B: one sampled run per seed and model
TEMPERATURE = 0.7                # section B sampling (greedy has no run-to-run variance)
TOP_P = 0.8
SEED_LIMIT = None                # section B samples per run: None = all 500 (~35–45 h),
                                 # 112 = the stratified subset used so far (~9 h)
"""

DATASET_INTRO = r"""
## 2. Dataset — check the one the main notebook built

Verifies the ground truth of `data\synthetic-v1` against the repo (seconds). If the dataset is
missing it is built again (deterministic, ~10 min). The evaluation runner also re-hashes every
image and ground-truth file before each run.
"""

A_INTRO = r"""
## A. Greedy decoding — all 500 test samples

The headline numbers on the whole held-out test split, with the same settings as the latest
runs: 896 px, 2048 tokens, greedy, runaway guard on. The fine-tuned model goes first.

| Cell | Run | Time (rough) |
| --- | --- | --- |
| A.2 | Fine-tuned (QLoRA) | ~5–6 h |
| A.3 | Zero-shot | ~6–8 h |
| A.4 | OCR baseline (CPU, needs Tesseract) | ~30 min |
| A.5 | Paired comparisons + results table | 1 min |
| A.6 | Hand-back zip — **send it before starting B** | 1 min |
"""

A_SETTINGS = r"""
# A.1 Final-evaluation helpers (sections A and B use them; re-run after a restart)
import gzip
import yaml

TEST_SIZE = 500
model_cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["model"]
MODEL_SLUG = model_cfg["id"].split("/")[-1].lower()
ADAPTER = RUN_DIR / "adapter"
VLM = ["--backend", "hf", "--model-id", model_cfg["id"], "--dtype", COMPUTE_DTYPE,
       "--device-map", "cuda:0", "--max-new-tokens", MAX_NEW_TOKENS]
if model_cfg.get("revision"):
    VLM += ["--revision", model_cfg["revision"]]
if RUNAWAY_GUARD:
    VLM.append("--runaway-guard")
GREEDY = {"qlora": f"{RUN_NAME}-final-greedy",
          "zeroshot": f"{MODEL_SLUG}-zeroshot-final-greedy",
          "baseline": "baseline-v1-final"}
COMPARE_A = EVAL_DIR / "comparisons-final-greedy"
COMPARE_B = EVAL_DIR / "comparisons-final-seeds"


def seed_name(model, seed):
    stem = RUN_NAME if model == "qlora" else f"{MODEL_SLUG}-zeroshot"
    return f"{stem}-final-t{TEMPERATURE:g}-s{seed}"


def current_gpu():
    smi = shutil.which("nvidia-smi")
    if not smi:
        return None
    names = subprocess.run([smi, "--query-gpu=name", "--format=csv,noheader"],
                           capture_output=True, text=True).stdout.strip().splitlines()
    return names[0].strip() if names else None


def finished(path, expected=TEST_SIZE):
    if not ((path / "summary.json").exists() and (path / "run.json").exists()):
        return False
    info = read_json(path / "run.json")
    return bool(info.get("completed_at")) and info.get("samples_done") == expected


def run_gpu(path):
    return read_json(path / "run.json").get("environment", {}).get("gpu") if (
        path / "run.json").exists() else None


def evaluate(name, *args, limit=None):
    # Run (or resume) one evaluation on the test split; skip it when finished
    out = EVAL_DIR / name
    if finished(out, limit or TEST_SIZE):
        print(f"{name}: done")
        return out
    command = ["module", "evaluation", "run", "--dataset", DATA_DIR, "--split", "test",
               "--out", out, "--image-max-side", IMAGE_MAX_SIDE, *args]
    if limit:
        command += ["--limit", limit]
    started = time.time()
    driver(*command, log=f"eval-{name}")
    info = read_json(out / "run.json")
    print(f"\n{name}: {info['samples_done']} samples ({(time.time() - started) / 3600:.2f} h "
          "in this session)")
    if info.get("errors"):
        print(f"Note: {info['errors']} sample(s) raised an error; they count as failures.")
    return out


def predictions(path):
    raw = path / "predictions.jsonl"
    text = raw.read_text(encoding="utf-8") if raw.exists() else gzip.decompress(
        (path / "predictions.jsonl.gz").read_bytes()).decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def by_level(path):
    # {level: (samples, cut off at the token limit, stopped by the guard, failed)}
    counts = {}
    for result in predictions(path):
        attempts = (result["prediction"].get("analysis") or {}).get("extraction", {}).get(
            "attempts", [])
        reasons = [a["output"].get("finish_reason") for a in attempts]
        level = result["attributes"]["level"]
        n, cut, stopped, failed = counts.get(level, (0, 0, 0, 0))
        counts[level] = (n + 1, cut + ("length" in reasons), stopped + ("runaway" in reasons),
                         failed + (not result["scores"]["has_graph"]))
    return counts


KEYS = ("node_f1", "edge_f1", "edge_strict_f1", "graph_similarity", "label_accuracy",
        "qa_accuracy", "diagram_type_accuracy", "valid_first_attempt", "valid_post_repair")


def results_table(runs, expected=TEST_SIZE):
    print(" | ".join(("run", "n", "node F1", "edge F1", "strict", "graph sim", "labels", "QA",
                      "type", "valid@1", "valid", "s/sample", "GPU")))
    for name, path in runs.items():
        if not finished(path, expected):
            print(f"{name} | not finished")
            continue
        summary = read_json(path / "summary.json")
        values = [summary["macro"].get(k, {}).get("mean") for k in KEYS]
        latency = summary.get("latency_ms", {}).get("mean")
        print(" | ".join([name, str(summary["samples"]),
                          *("–" if v is None else f"{v:.3f}" for v in values),
                          "–" if latency is None else f"{latency / 1000:.0f}",
                          str(run_gpu(path))]))
    print("\nper level: cut off / stopped by the guard / failed (of n), and graph similarity:")
    for name, path in runs.items():
        if finished(path, expected):
            levels = read_json(path / "summary.json")["breakdowns"]["level"]
            cells = [f"L{lv}: {c}/{s}/{f} of {n}, {levels[str(lv)]['graph_similarity']:.3f}"
                     for lv, (n, c, s, f) in sorted(by_level(path).items())]
            print(f"  {name:22s}", "  ".join(cells))


GPU = current_gpu()
if not (ADAPTER / "adapter_config.json").exists():
    raise RuntimeError(f"No trained adapter in {ADAPTER} — check ROOT and RUN_NAME in 1.1.")
print(f"GPU {GPU} | {IMAGE_MAX_SIDE} px | max_new_tokens {MAX_NEW_TOKENS} | "
      f"runaway guard {'on' if RUNAWAY_GUARD else 'off'} | adapter {ADAPTER}")
for name in GREEDY.values():
    path = EVAL_DIR / name
    state = (f"done on {run_gpu(path)}" if finished(path) else
             "started — its cell resumes it" if (path / "predictions.jsonl").exists() else "to run")
    print(f"  {name}: {state}")
"""

A_QLORA = r"""
# A.2 Fine-tuned model, greedy, all 500 (the most important run — resumable)
qlora_greedy = evaluate(GREEDY["qlora"], *VLM, "--adapter", ADAPTER)
"""

A_ZEROSHOT = r"""
# A.3 Zero-shot model, greedy, all 500 (resumable)
zeroshot_greedy = evaluate(GREEDY["zeroshot"], *VLM)
"""

A_BASELINE = r"""
# A.4 OCR baseline, all 500 (CPU; resumable)
if USE_BASELINE:
    baseline = evaluate(GREEDY["baseline"], "--backend", "baseline")
else:
    print("OCR baseline skipped: Tesseract was not found (section 1.3). The VLM results are "
          "unaffected; the repo has a 500-sample baseline run from another data build.")
"""

A_RESULTS = r"""
# A.5 Paired comparisons (§20.11) and results — paste this output back with the zip
runs_a = {model: EVAL_DIR / name for model, name in GREEDY.items()}
COMPARE_A.mkdir(parents=True, exist_ok=True)
for title, (a, b) in {"qlora-vs-zeroshot": ("zeroshot", "qlora"),
                      "qlora-vs-baseline": ("baseline", "qlora"),
                      "zeroshot-vs-baseline": ("baseline", "zeroshot")}.items():
    if finished(runs_a[a]) and finished(runs_a[b]):
        driver("module", "evaluation", "compare", "--a", runs_a[a], "--b", runs_a[b],
               "--out", COMPARE_A / f"{title}.md", log="compare-final")
    else:
        print(f"skipped {title}: not both finished")
print()
results_table(runs_a)
"""

A_HANDBACK = r"""
# A.6 Hand-back for section A — send this zip before starting section B
handback_a = OUT / "handback" / f"vigraph-handback-{RUN_NAME}-final-greedy.zip"
done_a = [path for path in runs_a.values() if finished(path)]
extra_a = sorted(COMPARE_A.glob("*")) + [DATA_DIR / "manifest.json"]
driver("handback", "--out", handback_a, "--eval", *done_a, "--extra", *extra_a, log="handback")
print("\nGive back:", handback_a)
"""

B_INTRO = r"""
## B. Sampling — 3 seeds per model

Run-to-run variance (§20.10). Greedy decoding gives the same answer every time, so the variance
comes from sampling: each model runs once per seed with `TEMPERATURE` and `TOP_P` (settings
1.1); everything else is as in section A. The runs alternate fine-tuned / zero-shot seed by
seed, so stopping early still leaves complete pairs.

With `SEED_LIMIT = None` every run covers all 500 samples (~35–45 h in total). To finish in
~9 h, set `SEED_LIMIT = 112` in 1.1 (the stratified subset used for every earlier comparison)
and re-run 1.1 and A.1 — before B.2 starts, not halfway.
"""

B_PLAN = r"""
# B.1 The sampled runs (needs A.1)
SAMPLING = ["--temperature", TEMPERATURE, "--top-p", TOP_P]
SEED_RUNS = [(model, seed) for seed in SEEDS for model in ("qlora", "zeroshot")]
SEED_EXPECTED = SEED_LIMIT or TEST_SIZE
print(f"temperature {TEMPERATURE}, top-p {TOP_P}, {SEED_EXPECTED} samples per run, "
      f"seeds {SEEDS} | GPU {GPU}")
for model, seed in SEED_RUNS:
    path = EVAL_DIR / seed_name(model, seed)
    state = (f"done on {run_gpu(path)}" if finished(path, SEED_EXPECTED) else
             "started — B.2 resumes it" if (path / "predictions.jsonl").exists() else "to run")
    print(f"  {seed_name(model, seed)}: {state}")
"""

B_RUN = r"""
# B.2 Run (or resume) every sampled run in order — after a stop, run 1, 2, A.1, B.1, then this
for model, seed in SEED_RUNS:
    args = [*VLM, *SAMPLING, "--seed", seed]
    if model == "qlora":
        args += ["--adapter", ADAPTER]
    evaluate(seed_name(model, seed), *args, limit=SEED_LIMIT)
"""

B_RESULTS = r"""
# B.3 Seed statistics and comparisons — paste this output back with the zip
groups = {model: [EVAL_DIR / seed_name(model, seed) for seed in SEEDS
                  if finished(EVAL_DIR / seed_name(model, seed), SEED_EXPECTED)]
          for model in ("qlora", "zeroshot")}
COMPARE_B.mkdir(parents=True, exist_ok=True)
for model, runs in groups.items():
    if len(runs) >= 2:
        driver("module", "evaluation", "seeds", *runs, "--out", COMPARE_B / f"{model}-seeds.md",
               log="seeds-final")
    else:
        print(f"{model}: {len(runs)} finished seed run(s) — at least 2 are needed for a spread")
if groups["qlora"] and groups["zeroshot"]:
    driver("module", "evaluation", "compare", "--a", *groups["zeroshot"], "--b", *groups["qlora"],
           "--out", COMPARE_B / "qlora-vs-zeroshot-seeds.md", log="compare-final")
if SEED_EXPECTED == TEST_SIZE:  # same samples as section A: sampling vs greedy
    for model in ("qlora", "zeroshot"):
        greedy = EVAL_DIR / GREEDY[model]
        if groups[model] and finished(greedy):
            driver("module", "evaluation", "compare", "--a", greedy, "--b", *groups[model],
                   "--out", COMPARE_B / f"{model}-sampled-vs-greedy.md", log="compare-final")
print()
results_table({seed_name(m, s): EVAL_DIR / seed_name(m, s) for m, s in SEED_RUNS}, SEED_EXPECTED)
"""

B_HANDBACK = r"""
# B.4 Hand-back for section B
handback_b = OUT / "handback" / f"vigraph-handback-{RUN_NAME}-final-seeds.zip"
done_b = [path for runs in groups.values() for path in runs]
driver("handback", "--out", handback_b, "--eval", *done_b,
       "--extra", *sorted(COMPARE_B.glob("*")), log="handback")
print("\nGive back:", handback_b)
"""

GIVE_BACK = r"""
### Files to give back

1. **After section A:** `E:\Asif\vigraph\output\handback\vigraph-handback-qwen3vl-2b-qlora-a6000-v1-final-greedy.zip`
   (~2 MB: the three runs with every raw output, the comparisons, the data manifest,
   `MANIFEST.json`) and the output of cell **A.5**.
2. **After section B:** `E:\Asif\vigraph\output\handback\vigraph-handback-qwen3vl-2b-qlora-a6000-v1-final-seeds.zip`
   and the output of cell **B.3**.

If a cell fails, send its output, or the matching log from `E:\Asif\vigraph\output\logs\`.
"""


def cells() -> list[dict]:
    return [
        md(INTRO),
        *setup_cells(),
        md(A_INTRO),
        code(A_SETTINGS),
        code(A_QLORA),
        code(A_ZEROSHOT),
        code(A_BASELINE),
        code(A_RESULTS),
        code(A_HANDBACK),
        md(B_INTRO),
        code(B_PLAN),
        code(B_RUN),
        code(B_RESULTS),
        code(B_HANDBACK),
        md(GIVE_BACK),
    ]


def build() -> dict:
    built = []
    for index, cell in enumerate(cells()):
        entry = {
            "cell_type": cell["cell_type"],
            "id": f"final-{index:02d}",
            "metadata": {},
            "source": cell["source"].splitlines(keepends=True),
        }
        if cell["cell_type"] == "code":
            entry.update(execution_count=None, outputs=[])
        built.append(entry)
    return {
        "cells": built,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (venv)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def render() -> str:
    return json.dumps(build(), indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    NOTEBOOK.write_text(render(), encoding="utf-8")
    print(f"wrote {NOTEBOOK} ({len(build()['cells'])} cells)")
