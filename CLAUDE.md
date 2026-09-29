# CLAUDE.md — Vi-Graph

Read this first in every session. The full specification is [`docs/SPEC.md`](docs/SPEC.md);
section numbers below (§N) refer to it. Update **Current status** at the end of every
work block (§33.1).

## Current status

```text
Phase: 0 — Project initialization (complete). Phase 1 starts next.
Last completed: Phase 0 — directory structure (§5), root config files, FastAPI skeleton
  with GET /health + settings + tests, Next.js skeleton showing backend status,
  Dockerfiles + docker-compose (both images built and run end-to-end), READMEs,
  research/error_taxonomy.md, research/experiment_matrix.md.
Next up: Phase 1, step 1 — canonical graph schema v2 as Pydantic models in
  backend/app/schemas/ (§7), with schema validation tests written alongside it (§33.3).
  Then: thin VLM interface + mock backend (backend/app/vlm/), prompt template with
  version hash (§8 Stage B), validation → retry → repair path (§8 Stage C), metadata
  logging from the first inference call (§18.1).
Open decisions made this session:
  - License: MIT (holder: asifuddin01).
  - Requirements split: requirements.txt (core, no torch) / requirements-dev.txt /
    requirements-vlm.txt (torch + transformers). Keeps tests/CI GPU-free.
  - VLM backend switch: VIGRAPH_VLM_BACKEND = "mock" | "hf" (default "mock").
  - Default model is TENTATIVE: Qwen/Qwen3-VL-2B-Instruct — confirm in Phase 1.
  - Frontend uses a system font stack (no next/font/google) so builds need no font download.
  - Test client dep is httpx2 (Starlette >= 1.7 deprecates httpx for TestClient).
Known issues / TODOs:
  - This cloud environment's network policy blocks huggingface.co, so real model
    weights cannot be downloaded here. Develop against the mock backend; test real
    inference where HF is reachable (or allow huggingface.co in the environment settings).
  - Docker builds inside this sandbox need the agent-proxy CA injected (verify-only, not
    committed). The committed Dockerfiles are standard and need no changes elsewhere.
  - §44.2 badge text says "node 18+"; Next 16 requires Node >= 20.9 — use that when badges
    are added (Phase 2).
  - frontend/app/favicon.ico is still the Next.js default.
```

## Static conventions

- **Names:** package/repo/paths `vigraph`; display name **Vi-Graph**.
- **Schema version in effect:** `"2.0"` (§7). Pinned in `backend/app/schemas/`. Every graph
  carries `schema_version`; unknown versions are rejected.
- **Node/edge matching (§20.1):** lives in `evaluation/metrics/matching.py`. Similarity
  function and threshold are **not yet locked** (spec suggests 0.7). Once chosen, they are
  a versioned, project-defining constant — record the decision here.
- **Non-negotiables:**
  - Never train on the test set; keep one untouched benchmark set.
  - Never silently repair or normalize model output — every correction is logged (§8 C/D).
  - Never build Mermaid from unvalidated text; escape all labels (§10, §29).
  - Log reproducibility metadata from the first inference call (§18.1): model + revision,
    prompt hash, decoding params, seed, schema_version, split hash.
  - Training happens only in Colab (T4). The backend only loads adapters (§18). Claude
    Code writes `training/`; the user runs it (§33.4).
  - Don't claim results/metrics that haven't been measured (§39).
- **Build order:** follow §31 / §42. Phases 1–3 (VLM → graph → QA) are one continuous
  thread. Commit at phase-sized granularity with descriptive messages (§33.2).

## Layout & commands

- Backend package is `app` under `backend/` (`uvicorn app.main:app` from `backend/`).
  Settings: `backend/app/config.py`, env prefix `VIGRAPH_` (see `.env.example`).
- Frontend: `frontend/` — Next.js 16 (App Router), React 19, Tailwind 4. This Next version
  has breaking changes; read `frontend/AGENTS.md` and `frontend/node_modules/next/dist/docs/`
  before framework-level changes.

```bash
# Backend (from repo root)
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .

# Frontend (from frontend/)
npm install && npm run lint && npm run typecheck && npm run build

# Full stack
docker compose up --build
```
