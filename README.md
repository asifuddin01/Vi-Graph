# Vi-Graph

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Node](https://img.shields.io/badge/node-20.9%2B-green)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![Next.js](https://img.shields.io/badge/frontend-Next.js-black)
![Status](https://img.shields.io/badge/status-research%20in%20progress-yellow)

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

> **Status:** Phases 1–3 complete (the usable product) — upload a diagram, get a validated,
> versioned JSON graph (with retry/repair and run logging), edit it interactively, ask
> topology questions with graph-grounded answers, and export JSON, Mermaid, SVG, PNG, or
> PDF. Research track: synthetic dataset (2,800 rendered diagrams with exact ground truth
> and a held-out-layout test split, see [`data/`](data/README.md)) and evaluation framework
> ([`evaluation/`](evaluation/README.md)) are done, with a classical OCR + geometry baseline
> measured, and the fine-tuned model is evaluated on the full test split
> ([results](research/experiment_matrix.md#final-evaluation--all-500-test-samples-headline)). See
> [`CLAUDE.md`](CLAUDE.md) for current status and [`docs/SPEC.md`](docs/SPEC.md) for the
> full specification.

**Lightweight fine-tuning.** Qwen3-VL-2B-Instruct is fine-tuned with 4-bit QLoRA (17.4 M
trainable parameters) in **1.4 hours on a single GPU using at most 7.6 GB of GPU memory**
(measured peak; PyTorch was capped at 10.5 GB) — small enough that a 12 GB consumer card or a
free Colab T4 should fit it, though it has not been run on those yet
([`training/`](training/README.md)). On the full held-out test split (500 diagrams) it
improves over the zero-shot model on every metric (edge F1 0.499 → 0.638, graph similarity
0.581 → 0.740, structural QA 0.437 → 0.582, valid graphs 72% → 91%; all significant in paired
tests) — see the
[results and caveats](research/experiment_matrix.md#final-evaluation--all-500-test-samples-headline).

## Repository layout

| Path          | Contents                                                              |
| ------------- | --------------------------------------------------------------------- |
| `backend/`    | FastAPI app: schemas, VLM interface, graph layer, QA, exporters       |
| `frontend/`   | Next.js + TypeScript + Tailwind UI                                    |
| `data/`       | Synthetic dataset generator, datasets, annotations, split manifests   |
| `training/`   | Colab (T4) LoRA/QLoRA notebooks and configs — training runs in Colab only |
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
