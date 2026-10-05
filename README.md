# Vi-Graph

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Node](https://img.shields.io/badge/node-20.9%2B-green)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![Next.js](https://img.shields.io/badge/frontend-Next.js-black)
![Status](https://img.shields.io/badge/status-v1%20complete-brightgreen)

**Vision-language diagram understanding, graph reconstruction, and multimodal reasoning.**

Vi-Graph takes a diagram image (a neural-network architecture, ML pipeline, flowchart,
system architecture, UML-like diagram, …), reconstructs its structure as a strict,
versioned JSON graph, renders it as an editable diagram and as Mermaid, and answers
topology-aware questions about it.

> **Research question:** How accurately can compact Vision-Language Models recover the
> structural relationships in visual diagrams, especially as diagram complexity increases?

```text
Diagram image → VLM → structured JSON → validate / normalize / repair
             → interactive graph → Mermaid · SVG · PNG · PDF · JSON
             → topology-aware question answering
```

> **Status:** complete (v1). The product works end to end: upload a diagram, get a validated,
> versioned JSON graph (with retry/repair and run logging), edit it interactively, ask topology
> questions with graph-grounded answers, and export JSON, Mermaid, SVG, PNG or PDF. The research
> track is done on a synthetic benchmark (2,800 rendered diagrams with exact ground truth and a
> held-out-layout test split, see [`data/`](data/README.md)) with a matching-based evaluation
> framework ([`evaluation/`](evaluation/README.md)), a classical OCR + geometry baseline and a
> QLoRA-fine-tuned VLM. Results below; full write-up in
> [`research/paper/report.md`](research/paper/report.md), every run in
> [`research/experiment_matrix.md`](research/experiment_matrix.md). See
> [`docs/SPEC.md`](docs/SPEC.md) for the specification.

**Lightweight fine-tuning.** Qwen3-VL-2B-Instruct is fine-tuned with 4-bit QLoRA (17.4 M
trainable parameters) in **1.4 hours on a single GPU using at most 7.6 GB of GPU memory**
(measured peak; PyTorch was capped at 10.5 GB) — small enough that a 12 GB consumer card or a
free Colab T4 should fit it, though it has not been run on those yet
([`training/`](training/README.md)). On the full held-out test split (500 diagrams) it
improves over the zero-shot model on every metric (edge F1 0.499 → 0.638, graph similarity
0.581 → 0.740, structural QA 0.437 → 0.582, valid graphs 72% → 91%; all significant in paired
tests) — see the
[results and caveats](research/experiment_matrix.md#final-evaluation--all-500-test-samples-headline).

## Results

All 500 held-out test diagrams (synthetic-v1; layouts and themes never seen in training), the
same images for every system, greedy decoding, one GPU; macro means, failures count as 0.

| System                        | Node F1 | Edge F1 | Graph similarity | Structural QA | Labels | Diagram type | Valid graphs |
| ----------------------------- | ------- | ------- | ---------------- | ------------- | ------ | ------------ | ------------ |
| OCR + geometry baseline       | 0.872   | 0.610   | 0.738            | 0.450         | 0.885  | 0.702        | 99.8%        |
| Qwen3-VL-2B zero-shot         | 0.703   | 0.499   | 0.581            | 0.437         | 0.979  | 0.334        | 72.0%        |
| **Qwen3-VL-2B + QLoRA**       | 0.854   | 0.638   | **0.740**        | **0.582**     | **0.984** | **0.882** | 91.0%        |

- **Fine-tuning helps on every metric** (paired bootstrap, Holm, p < 0.001). Over 3 sampling
  seeds the spread is ≤ 0.012 (graph similarity 0.748 ± 0.006 vs 0.582 ± 0.009).
- **Against the classical baseline** the fine-tuned model ties on overall structure and wins on
  labels, structural QA and diagram type, but its lead depends on size: graph similarity is
  ahead on small diagrams (L1 +0.057, L2 +0.093), level on mid-sized ones and behind on the
  densest (L4 −0.124).
- **Dense diagrams fail by runaway enumeration**: the model keeps listing invented nodes or
  edges until its token budget ends (45 of 125 L4 diagrams). Where it does return a graph at L4,
  it matches the baseline.
- **Validation, retry and repair** turn 72.8% usable first answers into 91.0%. A **runaway
  guard** cuts evaluation time by 26% at equal scores. Resolution matters below 768 px.

**Limitations:** synthetic diagrams only (no real-diagram benchmark), one model family and
size, no perturbation study, an uncalibrated matching threshold. See the
[report](research/paper/report.md#10-limitations).

## Repository layout

| Path          | Contents                                                              |
| ------------- | --------------------------------------------------------------------- |
| `backend/`    | FastAPI app: schemas, VLM interface, graph layer, QA, exporters       |
| `frontend/`   | Next.js + TypeScript + Tailwind UI                                    |
| `data/`       | Synthetic dataset generator, datasets, annotations, split manifests   |
| `training/`   | QLoRA training + evaluation notebooks (Colab T4, Windows GPU), configs, run metadata |
| `evaluation/` | Metrics (incl. node/edge matching), evaluation scripts, reports       |
| `research/`   | Experiment matrix, error taxonomy, paper drafts                       |
| `examples/`   | Example synthetic diagrams with their ground-truth graphs             |
| `docs/`       | Project specification                                                 |

## Getting started

Requirements: Python 3.11+, Node 20.9+ (22 recommended). No GPU is needed for
development — the backend defaults to a mock VLM.

```bash
cp .env.example .env
```

### Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cd backend && ../.venv/bin/uvicorn app.main:app --reload     # http://localhost:8000/health
```

Tests and lint (from the repo root):

```bash
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

`requirements.txt` holds the core runtime, `requirements-dev.txt` adds test tooling,
`requirements-vlm.txt` adds `torch`/`transformers`/`peft` for running a real model, and
`requirements-baseline.txt` adds OpenCV + pytesseract for the classical non-VLM baseline
(plus `apt-get install tesseract-ocr`). Evaluation is documented in
[`evaluation/README.md`](evaluation/README.md).

The backend uses a mock VLM by default. To run a real model (needs a GPU and access to
huggingface.co):

```bash
.venv/bin/pip install -r requirements-vlm.txt
cd backend
VIGRAPH_VLM_BACKEND=hf VIGRAPH_VLM_DTYPE=float16 ../.venv/bin/python -m app.vlm diagram.png
```

`python -m app.vlm` prints the raw model output and its reproducibility metadata.

SVG/PNG/PDF export needs [Graphviz](https://graphviz.org/) (`apt install graphviz` /
`brew install graphviz`); without it, JSON and Mermaid export still work.

### API

| Endpoint                   | Purpose                                                        |
| -------------------------- | -------------------------------------------------------------- |
| `POST /api/analyze`        | Multipart `file` (PNG/JPEG/WebP) → graph, status, raw outputs  |
| `GET /api/analyses/{id}`   | A stored analysis (with its latest saved edit)                 |
| `PUT /api/analyses/{id}/graph` | Save an edited graph as a new version                      |
| `POST /api/export`         | `json`, `mermaid`, `svg`, `png`, `pdf` of an analysis or graph |
| `POST /api/qa`             | Answer a question about an analysis, grounded in graph nodes   |
| `GET /api/analyses/{id}/qa` | Questions asked about an analysis                             |
| `GET /health`              | Liveness + active VLM backend                                  |

Every analysis is logged to `$VIGRAPH_STORAGE_DIR/vigraph.sqlite3` with the model revision,
prompt hashes, decoding parameters, and seed.

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
npm run lint && npm run typecheck && npm test
```

### Docker

```bash
docker compose up --build
```

Frontend on http://localhost:3000, backend on http://localhost:8000. The backend image
runs the mock VLM.

## License

[MIT](LICENSE)
