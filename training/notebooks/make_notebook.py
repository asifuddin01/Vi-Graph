"""Generate vigraph_qlora_t4.ipynb (the Colab training notebook) from this script.

    python training/notebooks/make_notebook.py

Edit the cells here, not in the .ipynb, so changes stay reviewable; the test suite checks
that the committed notebook matches this script and that every code cell parses.
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK = Path(__file__).with_name("vigraph_qlora_t4.ipynb")

CELLS: list[tuple[str, str]] = []


def md(text: str) -> None:
    CELLS.append(("markdown", text.strip("\n")))


def code(text: str) -> None:
    CELLS.append(("code", text.strip("\n")))


# --- 0. Overview ------------------------------------------------------------------------

md(r"""
# Vi-Graph — QLoRA fine-tuning on a Colab T4

Fine-tunes a compact VLM (Qwen3-VL-2B-Instruct, 4-bit QLoRA) to turn diagram images into
schema-v2 graph JSON, then evaluates it against the zero-shot model and the classical
baseline — all with the repo's own pipeline and metrics (spec §17–§21).

**Before you start:** *Runtime → Change runtime type → T4 GPU*. Then run the sections in
order. Everything that matters is written to Google Drive (`DRIVE_DIR`).

| Section | What it does | Time (T4, rough) |
| --- | --- | --- |
| 1. Setup | GPU check, Drive, code, libraries, imports | ~5 min |
| 2. Dataset | Build synthetic-v1 (deterministic), verify against the repo | ~5 min |
| 3. Preprocess | Training examples + token-length check | ~3 min |
| 4. Model | Smoke run: 4-bit model + LoRA, 2 steps, adapter reload | ~10 min |
| 5. Train | Full QLoRA run — **resumable** | hours (projected in §4) |
| 6. Evaluation | Zero-shot vs fine-tuned vs baseline on the test split — **resumable** | ~1–2 h per model |
| 7. Save & hand back | One zip with everything Claude needs | ~1 min |

**If Colab disconnects:** reconnect, run sections **1 and 2** again (they are quick and
skip finished work), then re-run the cell you were in. Training resumes from its last
checkpoint on Drive; evaluation resumes from its last finished sample. Nothing is lost
except the step in flight.

**Never train on the test split** — the code refuses to.
""")

# --- 1. Setup ---------------------------------------------------------------------------

md(r"""
## 1. Setup — GPU, Drive, code, libraries, imports

Edit the settings cell if needed, then run all of section 1.
""")

code(r"""
# ---- Settings (edit here) ------------------------------------------------------------
REPO_URL = "https://github.com/asifuddin01/Vi-Graph.git"
BRANCH = "claude/tender-ramanujan-70dwgj"
REPO = "/content/Vi-Graph"
DRIVE_DIR = "/content/drive/MyDrive/vigraph"  # checkpoints, adapter, evaluations, hand-back
DATA_DIR = "/content/data/synthetic-v1"       # local disk (fast); rebuilt after a disconnect
CONFIG = "training/configs/qlora_t4.yaml"
EVAL_LIMIT = 112     # test samples per evaluation: a stratified prefix (4 × every level ×
                     # diagram type). None = all 500 (≈4× longer).
RUN_BASELINE = True  # classical OCR baseline on this same data build (CPU, a few minutes)
""")

code(r"""
# GPU check
!nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
import torch

assert torch.cuda.is_available(), "No GPU: Runtime → Change runtime type → T4 GPU"
gpu = torch.cuda.get_device_name(0)
print("GPU:", gpu, "| torch", torch.__version__, "| CUDA", torch.version.cuda)
if "T4" not in gpu:
    print("Note: configs are sized for a T4; other GPUs work but timings will differ.")
""")

code(r"""
# Google Drive: everything worth keeping goes here
from google.colab import drive

drive.mount("/content/drive")
import os

os.makedirs(DRIVE_DIR, exist_ok=True)
print("Drive dir:", DRIVE_DIR)
""")

code(r"""
# Code: clone the repo (or update it). For a private repo, add a GitHub token as a Colab
# secret named GITHUB_TOKEN (key icon in the left sidebar).
import subprocess

url = REPO_URL
try:
    from google.colab import userdata

    token = userdata.get("GITHUB_TOKEN")
    if token:
        url = REPO_URL.replace("https://", f"https://{token}@")
except Exception:
    pass
if not os.path.exists(REPO):
    subprocess.run(["git", "clone", "--branch", BRANCH, url, REPO], check=True)
else:
    subprocess.run(["git", "-C", REPO, "fetch", "origin", BRANCH], check=True)
    subprocess.run(["git", "-C", REPO, "checkout", BRANCH], check=True)
    subprocess.run(["git", "-C", REPO, "pull", "--ff-only", "origin", BRANCH], check=True)
os.chdir(REPO)
print(subprocess.run(["git", "log", "-1", "--oneline"], capture_output=True, text=True).stdout)
""")

code(r"""
# Libraries: Graphviz (dataset rendering), Tesseract (baseline), Python packages.
# Colab's own numpy / scipy / pillow / torch are pinned as pip constraints so nothing can
# replace them (a replaced numpy breaks preinstalled packages and needs a runtime restart).
!apt-get -qq update > /dev/null 2>&1
!apt-get -qq install -y graphviz fonts-dejavu-core tesseract-ocr > /dev/null
!pip freeze | grep -iE "^(numpy|scipy|pillow|torch|torchvision|torchaudio)==" > /content/colab-constraints.txt
!pip install -q -r requirements-train.txt -c /content/colab-constraints.txt
!dot -V
!tesseract --version | head -n 1
from importlib.metadata import version as installed

print("kept from Colab:", open("/content/colab-constraints.txt").read().split())
print("numpy", installed("numpy"), "| torch", installed("torch"),
      "| transformers", installed("transformers"))
""")

code(r"""
# Imports and paths (the repo's backend/ and root must be importable)
import gc
import json
import sys
from pathlib import Path

for path in (REPO, f"{REPO}/backend"):
    if path not in sys.path:
        sys.path.insert(0, path)
os.environ["PYTHONPATH"] = f"{REPO}/backend:{REPO}"

import transformers, peft, bitsandbytes, accelerate  # noqa: E401 — fail fast if missing

from training.qlora.config import load_config
from training.qlora.data import load_training_split, build_example
from training.qlora.train import environment, projected_hours, run_training, total_steps
from training.qlora.handback import package_handback

print({"transformers": transformers.__version__, "peft": peft.__version__,
       "bitsandbytes": bitsandbytes.__version__, "accelerate": accelerate.__version__})
config = load_config(Path(CONFIG))
RUN_DIR = Path(DRIVE_DIR) / "runs" / config.run_name
EVAL_DIR = Path(DRIVE_DIR) / "eval"
print("Run:", config.run_name, "| model", config.model.id, "| run dir", RUN_DIR)
""")

# --- 2. Dataset -------------------------------------------------------------------------

md(r"""
## 2. Dataset — build synthetic-v1 and verify it

The generator is deterministic, so this rebuilds exactly the repo's dataset: 2,000 train /
300 val / 500 test. Images depend on the Graphviz version, so they may differ in pixels
from the build committed in the repo — but the **ground truth must be identical**, which
`verify --reference` checks. Training and evaluation record this build's split hashes and
refuse to resume on a different build.
""")

code(r"""
manifest_path = Path(DATA_DIR) / "manifest.json"
if not manifest_path.exists():
    !python -m data.generator build --out {DATA_DIR} --workers 2
!python -m data.generator verify {DATA_DIR} --reference data/splits/synthetic-v1.manifest.json
manifest = json.loads(manifest_path.read_text())
print("Graphviz:", manifest["graphviz_version"], "| dataset hash", manifest["dataset_hash"][:12])
""")

code(r"""
# Look at one training sample and its ground truth
from IPython.display import Image as ShowImage, display

sample_graph = Path(DATA_DIR) / "graphs" / "train-000009.json"
display(ShowImage(filename=str(Path(DATA_DIR) / "images" / "train-000009.png"), width=700))
print(sample_graph.read_text()[:1200], "…")
""")

# --- 3. Preprocess ----------------------------------------------------------------------

md(r"""
## 3. Preprocess — training examples

Each example is exactly what the app sends at inference (Stage A resize to
`image_max_side`, the `graph_extraction@1` prompt) with the ground truth as the answer
(compact JSON). The loss covers only the answer: the check below prints what the model is
trained on — it must start with `{"schema_version":"2.0"` and end with the end-of-turn token.
""")

code(r"""
from transformers import AutoProcessor
from training.qlora.collate import Collator

train_info, train_samples = load_training_split(Path(DATA_DIR), config.data.train_split)
val_info, val_samples = load_training_split(Path(DATA_DIR), config.data.eval_split)
print(f"train {len(train_samples)} (hash {train_info.split_hash[:12]}), "
      f"val {len(val_samples)} (hash {val_info.split_hash[:12]})")

processor = AutoProcessor.from_pretrained(config.model.id, revision=config.model.revision)
collator = Collator(processor)
example = build_example(train_samples[9], config.data.image_max_side)
trained = collator.trained_text(example)
print("Trained on:", trained[:160], "…", trained[-40:])
assert trained.startswith('{"schema_version":"2.0"'), "label masking looks wrong — stop here"
""")

code(r"""
# Token lengths (image + prompt + answer) on a spread of samples: must fit a T4
import statistics

lengths, answers = [], []
for sample in train_samples[::50]:
    ex = build_example(sample, config.data.image_max_side)
    batch = collator([ex])
    lengths.append(batch["input_ids"].shape[1])
    answers.append(int((batch["labels"] != -100).sum()))
print(f"sequence tokens: mean {statistics.mean(lengths):.0f}, max {max(lengths)}; "
      f"answer tokens: mean {statistics.mean(answers):.0f}, max {max(answers)}")
if max(lengths) > 6000:
    print("Warning: long sequences — consider a smaller data.image_max_side in the config.")
""")

# --- 4. Model ---------------------------------------------------------------------------

md(r"""
## 4. Model — smoke run (do not skip)

Loads the model in 4-bit, attaches LoRA, trains **2 optimizer steps on 8 examples**, saves an
adapter, and loads it back through the app's own inference pipeline on one image. It catches
library/API problems in minutes instead of hours into training, measures speed and memory,
and projects the full run's duration. Output quality here is meaningless.
""")

code(r"""
import shutil

smoke_dir = Path(DRIVE_DIR) / "runs" / "_smoke"
shutil.rmtree(smoke_dir, ignore_errors=True)
smoke = load_config(Path(CONFIG), **{
    "run_name": "smoke", "data.train_limit": 8, "data.eval_samples": 2,
    "optimization.max_steps": 2, "optimization.gradient_accumulation_steps": 4,
    "checkpointing.save_steps": 1, "checkpointing.eval_steps": 2, "checkpointing.logging_steps": 1,
})
result = run_training(smoke, Path(DATA_DIR), smoke_dir)
gc.collect(); torch.cuda.empty_cache()

meta = json.loads(Path(result.metadata_path).read_text())
log = [json.loads(line) for line in (smoke_dir / "train_log.jsonl").read_text().splitlines()]
speed = next(entry for entry in reversed(log) if "train_samples_per_second" in entry)
seconds_per_sample = 1 / speed["train_samples_per_second"]
print(f"trainable params {meta['trainable_parameters']:,} of {meta['total_parameters']:,}; "
      f"peak GPU memory {meta['peak_gpu_memory_gb']:.1f} GB; {seconds_per_sample:.1f} s/sample")
steps = total_steps(len(train_samples), config.optimization.epochs,
                    config.optimization.gradient_accumulation_steps, config.optimization.max_steps)
hours = projected_hours(seconds_per_sample, len(train_samples), config.optimization.epochs)
print(f"Full run: {steps} optimizer steps, ≈ {hours:.1f} h of training "
      f"(checkpoint every {config.checkpointing.save_steps} steps)")
""")

code(r"""
# The smoke adapter through the app's pipeline (Stages A–D) on one val image
!rm -rf /content/tmp/smoke-eval
!python -m evaluation run --dataset {DATA_DIR} --split val --limit 1 --backend hf --dtype float16 \
    --adapter {smoke_dir}/adapter --image-max-side {config.data.image_max_side} \
    --max-new-tokens 256 --out /content/tmp/smoke-eval
""")

# --- 5. Train ---------------------------------------------------------------------------

md(r"""
## 5. Train — full QLoRA run (resumable)

Checkpoints go to `RUN_DIR/checkpoints` on Drive every `save_steps` optimizer steps. **After a
disconnect:** re-run sections 1–2, then this cell — it resumes from the latest checkpoint
(the run directory refuses a different config or data build). When it finishes, the adapter
is in `RUN_DIR/adapter` and the §18.1 metadata in `RUN_DIR/training_run.json`.
""")

code(r"""
finished = RUN_DIR / "training_run.json"
if finished.exists() and (RUN_DIR / "adapter" / "adapter_config.json").exists():
    print("Already trained:", json.loads(finished.read_text())["completed_at"])
else:
    result = run_training(config, Path(DATA_DIR), RUN_DIR)
    gc.collect(); torch.cuda.empty_cache()
    print(result)
""")

code(r"""
# Loss curves
import matplotlib.pyplot as plt

log = [json.loads(line) for line in (RUN_DIR / "train_log.jsonl").read_text().splitlines()]
train = [(e["step"], e["loss"]) for e in log if "loss" in e]
evals = [(e["step"], e["eval_loss"]) for e in log if "eval_loss" in e]
plt.figure(figsize=(8, 4))
plt.plot(*zip(*train), label="train loss")
if evals:
    plt.plot(*zip(*evals), "o-", label="val loss")
plt.xlabel("optimizer step"); plt.ylabel("loss"); plt.legend(); plt.grid(alpha=0.3)
plt.show()
""")

# --- 6. Evaluation ----------------------------------------------------------------------

md(r"""
## 6. Evaluation — zero-shot vs fine-tuned vs baseline (resumable)

Each run scores the held-out **test** split (layouts and themes never seen in training)
with the repo's evaluation runner: the full pipeline (Stages A–D), greedy decoding, the same
image size as training. Runs are written to Drive sample by sample — **after a disconnect,
re-run sections 1–2 and this cell**; finished runs are skipped, unfinished ones resume.
The paired comparisons (§20.11) need the same samples, so all runs use `EVAL_LIMIT`.
""")

code(r"""
import subprocess

def evaluate(name, *args):
    out = EVAL_DIR / name
    if (out / "summary.json").exists() and (out / "run.json").exists():
        run = json.loads((out / "run.json").read_text())
        if run.get("completed_at") and run.get("samples_done") == (EVAL_LIMIT or 500):
            print(f"{name}: done"); return out
    command = [sys.executable, "-m", "evaluation", "run", "--dataset", DATA_DIR, "--split", "test",
               "--out", str(out), "--image-max-side", str(config.data.image_max_side), *args]
    if EVAL_LIMIT:
        command += ["--limit", str(EVAL_LIMIT)]
    subprocess.run(command, check=True)
    return out

hf = ["--backend", "hf", "--model-id", config.model.id, "--dtype", "float16",
      "--max-new-tokens", "2048"]
if config.model.revision:
    hf += ["--revision", config.model.revision]
model_slug = config.model.id.split("/")[-1].lower()
runs = {
    "zeroshot": evaluate(f"{model_slug}-zeroshot-s0", *hf),
    "qlora": evaluate(f"{config.run_name}-s0", *hf, "--adapter", str(RUN_DIR / "adapter")),
}
if RUN_BASELINE:
    runs["baseline"] = evaluate("baseline-v1-colab", "--backend", "baseline")
""")

code(r"""
# Paired significance tests (§20.11): fine-tuned vs zero-shot, and each VLM vs the baseline
comparisons = EVAL_DIR / "comparisons"
comparisons.mkdir(parents=True, exist_ok=True)
pairs = [("zeroshot", "qlora")]
if "baseline" in runs:
    pairs += [("baseline", "zeroshot"), ("baseline", "qlora")]
for a, b in pairs:
    !python -m evaluation compare --a {runs[a]} --b {runs[b]} --out {comparisons}/{b}-vs-{a}.md
""")

code(r"""
# Headline table
rows = []
for name, path in runs.items():
    summary = json.loads((path / "summary.json").read_text())
    m = summary["macro"]
    rows.append((name, *(m[k]["mean"] for k in ("node_f1", "edge_f1", "edge_strict_f1",
                "graph_similarity", "label_accuracy", "qa_accuracy", "valid_first_attempt",
                "valid_post_repair"))))
header = ("run", "node F1", "edge F1", "strict", "graph sim", "labels", "QA", "valid@1", "valid")
print(" | ".join(header))
for row in rows:
    print(" | ".join([row[0]] + ["–" if v is None else f"{v:.3f}" for v in row[1:]]))
""")

# --- 7. Save & hand back ----------------------------------------------------------------

md(r"""
## 7. Save & hand back

Packs everything Claude needs into **one zip on your Drive** — the adapter, training
metadata and loss log, every evaluation run (with per-sample predictions), the comparisons,
this data build's manifest, and the environment. Download it and give it back in the
Claude Code session.
""")

code(r"""
handback = Path(DRIVE_DIR) / "handback" / f"vigraph-handback-{config.run_name}.zip"
manifest = package_handback(
    handback,
    training_dirs=[RUN_DIR],
    eval_dirs=list(runs.values()),
    extra_files=sorted(comparisons.glob("*")) + [Path(DATA_DIR) / "manifest.json"],
    environment=environment(),
)
size = handback.stat().st_size / 1024**2
print(f"Hand-back: {handback} ({size:.1f} MB, {len(manifest['files'])} files)")
if manifest["missing"]:
    print("Missing (re-run the section that produces them):", *manifest["missing"], sep="\n  ")
""")

md(r"""
### Files to give back

Give back **`vigraph-handback-<run_name>.zip`** from `DRIVE_DIR/handback/`. It contains:

| In the zip | What it is |
| --- | --- |
| `training/<run>/adapter/adapter_model.safetensors`, `adapter_config.json` | The trained LoRA adapter |
| `training/<run>/training_run.json` | §18.1 metadata: model + revision, LoRA, quantization, prompt hash, seed, split hashes, hyperparameters, losses, GPU, versions |
| `training/<run>/train_log.jsonl`, `run_config.json` | Every logged step; the exact config + data fingerprint |
| `evaluation/<run>/run.json`, `summary.json`, `report.md`, `predictions.jsonl.gz` | Zero-shot, fine-tuned and baseline evaluations with every raw model output |
| `extra/*-vs-*.md`, `.json`, `manifest.json` | Paired comparisons; this data build's manifest |
| `MANIFEST.json` | Every file with size and sha256, anything missing, the environment |

Also mention anything unusual you saw (errors, restarts, very slow steps). If a cell fails,
copy its full error output — the smoke run (section 4) exists to surface problems early.
""")


def build() -> dict:
    cells = []
    for kind, source in CELLS:
        lines = source.splitlines(keepends=True)
        cell = {"cell_type": kind, "metadata": {}, "source": lines}
        if kind == "code":
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    return {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"gpuType": "T4", "provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }


def render() -> str:
    return json.dumps(build(), indent=1, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    NOTEBOOK.write_text(render())
    print(f"wrote {NOTEBOOK} ({len(CELLS)} cells)")
