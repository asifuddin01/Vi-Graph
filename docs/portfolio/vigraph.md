---
title: "Vi-Graph: turning diagram images into editable, queryable graphs"
summary: "A fine-tuned 2B vision-language model reads diagrams (ML pipelines, flowcharts, system architectures) and rebuilds them as validated JSON graphs you can edit, export and ask questions about. Includes a full app, a 2,800-diagram benchmark and a statistically tested evaluation."
date: 2026-10
tags: [Vision-Language Models, QLoRA, Fine-tuning, Evaluation, FastAPI, Next.js, React Flow, Python, TypeScript]
cover: https://raw.githubusercontent.com/asifuddin01/Vi-Graph/claude/tender-ramanujan-70dwgj/docs/demo/vigraph-analyze.png
repo: https://github.com/asifuddin01/Vi-Graph
---

<!--
Notes for whoever adds this page to the portfolio (e.g. Claude Code):
- Media is hosted in the Vi-Graph repo (branch claude/tender-ramanujan-70dwgj, folder docs/demo/).
  Prefer copying these files into the portfolio's own assets and updating the paths over
  hotlinking: vigraph-demo.mp4 (53 s, 1920x1200, 2.7 MB), vigraph-demo.gif (3.6 MB),
  vigraph-analyze.png, vigraph-qa.png, vigraph-ml-pipeline.png, vigraph-system-architecture.png.
- Adapt the frontmatter fields to the portfolio's content schema; drop any it doesn't use.
- Every number below is measured and published in the repo. Don't round them up or add new ones.
- Keep the demo caption's note about replayed model output.
-->

# Vi-Graph

**Diagram image → validated graph → interactive editor → graph-grounded answers.**

Vi-Graph takes a picture of a diagram, such as a neural-network architecture, an ML pipeline,
a flowchart or a system architecture, and reconstructs its structure as a strict, versioned
JSON graph. You can edit the graph in the browser, export it to Mermaid, SVG, PNG, PDF or
JSON, and ask questions about it ("What feeds into X?", "Which branches run in parallel?").
Answers come from the graph and highlight the nodes they are based on.

The research question behind it: **how accurately can a compact vision-language model recover
the structure of a diagram, and how does that change as diagrams get more complex?**

![Vi-Graph demo: upload a diagram, get a validated graph, edit it and ask questions](https://raw.githubusercontent.com/asifuddin01/Vi-Graph/claude/tender-ramanujan-70dwgj/docs/demo/vigraph-demo.gif)

*53-second walkthrough ([full-resolution MP4](https://github.com/asifuddin01/Vi-Graph/blob/claude/tender-ramanujan-70dwgj/docs/demo/vigraph-demo.mp4)).
The model's outputs in the demo are replayed from the recorded evaluation run of the
fine-tuned model; everything after the model runs live.*

## Highlights

- **Fine-tuned a 2B VLM within a consumer-GPU memory budget.** Qwen3-VL-2B-Instruct with 4-bit
  QLoRA: 17.4 M trainable parameters, 250 steps, **1.4 hours**, **7.6 GB peak GPU memory**.
- **Large, significant gains over the base model** on 500 held-out test diagrams:
  graph similarity 0.581 → **0.740**, edge F1 0.499 → **0.638**, structural QA accuracy
  0.437 → **0.582**, valid graphs 72% → **91%**. Every metric improved, with p < 0.001
  (paired bootstrap, Holm-corrected). Stable across sampling seeds (graph similarity
  0.748 ± 0.006).
- **An honest baseline comparison.** A classical OCR + OpenCV pipeline I built ties the
  fine-tuned model on overall structure. The model wins on labels, question answering and
  diagram type. It leads on small diagrams and falls behind on the densest ones.
- **A full product, not just a notebook:** FastAPI backend, Next.js editor, exports,
  question answering and reproducible run logging. 767 automated tests.

## What I built

### 1. The app

- **Reconstruction pipeline.** The image is preprocessed, then the VLM is prompted for
  schema-constrained JSON. The output is validated against a strict schema, gets one
  corrective retry, and is repaired by a conservative programmatic step. Then it is
  normalized. Every correction is logged, never applied silently.
- **Interactive editor** (React Flow + ELK auto-layout). Move, rename, retype, add and
  delete nodes and edges; group and ungroup; inspect; save as numbered versions. The model's
  original output is never overwritten.
- **Graph-grounded question answering.** A rule-based router plus entity linking answers
  structural questions (predecessors, paths, parallel branches, merge points, counts)
  straight from the graph and highlights the grounding nodes. Only visual questions go back
  to the VLM with the image.
- **Exports:** Mermaid (escaping checked against the real Mermaid parser in a headless
  browser), plus SVG, PNG and PDF via Graphviz, and JSON.
- **Reproducibility by design.** Every inference logs model + revision, adapter, prompt
  hash, decoding parameters, seed, schema version and dataset split hash in SQLite.

| Diagram → editable graph | Graph-grounded answers |
| --- | --- |
| ![Scientific workflow reconstructed as an editable graph](https://raw.githubusercontent.com/asifuddin01/Vi-Graph/claude/tender-ramanujan-70dwgj/docs/demo/vigraph-analyze.png) | ![A question answered from the graph, with its nodes highlighted](https://raw.githubusercontent.com/asifuddin01/Vi-Graph/claude/tender-ramanujan-70dwgj/docs/demo/vigraph-qa.png) |
| ![ML pipeline with a Yes/No decision](https://raw.githubusercontent.com/asifuddin01/Vi-Graph/claude/tender-ramanujan-70dwgj/docs/demo/vigraph-ml-pipeline.png) | ![System architecture with a group and dependency edges](https://raw.githubusercontent.com/asifuddin01/Vi-Graph/claude/tender-ramanujan-70dwgj/docs/demo/vigraph-system-architecture.png) |

### 2. The benchmark

Real diagram datasets rarely come with exact structural ground truth, so I built a
**synthetic benchmark, synthetic-v1**:

- 2,800 rendered diagrams (2,000 train / 300 val / 500 test) with exact ground-truth graphs;
- 7 diagram types and 4 difficulty levels (3–6 up to 25–40 nodes, with groups, cycles,
  decisions and labeled edges);
- randomized visual themes and Graphviz layouts;
- the **test split uses layouts and themes never seen in training**, so it measures
  generalization rather than memorization;
- deterministic builds pinned by split hashes.

### 3. The evaluation framework

- **Node and edge matching** with Hungarian assignment over label similarity. **Graph
  similarity** is the primary metric: an edit-cost score, tested to be an upper bound on
  exact graph edit distance.
- A **structural QA benchmark** of 25,698 questions generated from the ground truth and
  answered on the predicted graph.
- Validity is measured both before and after repair. There is an automatic error taxonomy
  (missing, spurious, reversed and wrong edges; broken forks and merges).
- **Statistics:** paired bootstrap with 10,000 resamples and Holm–Bonferroni correction
  across metrics, plus t-tests and Wilcoxon tests; 3 sampling seeds for variance.

### 4. Training

QLoRA with 4-bit NF4 quantization and LoRA rank 16 on the language model's attention and MLP
projections; loss only on the answer tokens. It ran from a resumable notebook on a Windows
workstation (RTX A6000, PyTorch capped at 10.5 GB of VRAM). The trained adapter is in the
repository.

## Results

All 500 held-out test diagrams, the same images for every system, greedy decoding.
Macro means; a failed output counts as 0.

| System | Node F1 | Edge F1 | Graph similarity | Structural QA | Diagram type | Valid graphs |
| --- | --- | --- | --- | --- | --- | --- |
| OCR + OpenCV baseline | 0.872 | 0.610 | 0.738 | 0.450 | 0.702 | 99.8% |
| Qwen3-VL-2B zero-shot | 0.703 | 0.499 | 0.581 | 0.437 | 0.334 | 72.0% |
| **Qwen3-VL-2B + QLoRA** | 0.854 | **0.638** | **0.740** | **0.582** | **0.882** | 91.0% |

**What I learned from the analysis:**

- **Dense diagrams fail in one specific way.** On the largest diagrams (25–40 nodes), the
  model sometimes keeps listing invented nodes or edges until it runs out of tokens. I named
  this *runaway enumeration*. It explains the fine-tuned model's deficit against the
  baseline there: where it does return a graph, it matches the baseline.
- **I built an inference-time "runaway guard"** that detects these loops while the model
  generates and stops them early. It cut evaluation time by 26% with no significant change
  in any score.
- **Validation and repair matter.** The retry-and-repair stage turns 72.8% usable first
  answers into 91.0%.
- **Resolution has a floor.** Images downscaled to 640 px scored worse; 768, 896 and 1024 px
  scored the same.

## Limitations

All results are on synthetic diagrams; there is no real-diagram benchmark yet. Only one model
family and size was tested. The label-matching threshold hasn't been calibrated on
hand-labeled real data. These are listed as future work in the
[project report](https://github.com/asifuddin01/Vi-Graph/blob/claude/tender-ramanujan-70dwgj/research/paper/report.md).

## Tech stack

**ML:** PyTorch, Hugging Face Transformers, PEFT (LoRA/QLoRA), bitsandbytes, Qwen3-VL ·
**Evaluation:** NumPy, SciPy, NetworkX, RapidFuzz, OpenCV, Tesseract · **Backend:** Python,
FastAPI, Pydantic, SQLite, Graphviz · **Frontend:** TypeScript, Next.js, React, Tailwind CSS,
React Flow, ELK, Mermaid · **Tooling:** pytest (767 tests), Vitest, Ruff, Docker, Playwright

## Links

- Code: [github.com/asifuddin01/Vi-Graph](https://github.com/asifuddin01/Vi-Graph)
- Report: [research/paper/report.md](https://github.com/asifuddin01/Vi-Graph/blob/claude/tender-ramanujan-70dwgj/research/paper/report.md)
- Demo video: [vigraph-demo.mp4](https://github.com/asifuddin01/Vi-Graph/blob/claude/tender-ramanujan-70dwgj/docs/demo/vigraph-demo.mp4)
- Trained adapter: [models/qwen3vl-2b-qlora-a6000-v1](https://github.com/asifuddin01/Vi-Graph/tree/claude/tender-ramanujan-70dwgj/models/qwen3vl-2b-qlora-a6000-v1)

*Built with [Claude Code](https://claude.ai/code) as an AI pair programmer. I designed and
directed the project and ran all training and GPU evaluation on my own hardware.*
