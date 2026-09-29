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
> PDF. Research track: the synthetic dataset generator is done (2,800 rendered diagrams with
> exact ground truth and a held-out-layout test split, see [`data/`](data/README.md));
> evaluation and training come next. See
> [`CLAUDE.md`](CLAUDE.md) for current status and [`docs/SPEC.md`](docs/SPEC.md) for the
> full specification.

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

`requirements.txt` holds the core runtime, `requirements-dev.txt` adds test tooling, and
`requirements-vlm.txt` adds `torch`/`transformers`/`peft` for running a real model.

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
