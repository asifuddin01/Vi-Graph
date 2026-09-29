# Vi-Graph

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

> **Status:** Phase 0 (project skeleton). Nothing below the skeleton is implemented yet;
> see [`CLAUDE.md`](CLAUDE.md) for current status and [`docs/SPEC.md`](docs/SPEC.md) for
> the full specification.

## Repository layout

| Path          | Contents                                                              |
| ------------- | --------------------------------------------------------------------- |
| `backend/`    | FastAPI app: schemas, VLM interface, graph layer, QA, exporters       |
| `frontend/`   | Next.js + TypeScript + Tailwind UI                                    |
| `data/`       | Synthetic + real diagram datasets, annotations, split manifests       |
| `training/`   | Colab (T4) LoRA/QLoRA notebooks and configs — training runs in Colab only |
| `evaluation/` | Metrics (incl. node/edge matching), evaluation scripts, reports       |
| `research/`   | Experiment matrix, error taxonomy, paper drafts                       |
| `examples/`   | Example diagrams and outputs                                          |
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
`requirements-vlm.txt` adds `torch`/`transformers` for running a real model locally.

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
npm run lint && npm run typecheck
```

### Docker

```bash
docker compose up --build
```

Frontend on http://localhost:3000, backend on http://localhost:8000. The backend image
runs the mock VLM.

## License

[MIT](LICENSE)
