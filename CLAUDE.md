# CLAUDE.md — Vi-Graph

Read this first in every session. The full specification is [`docs/SPEC.md`](docs/SPEC.md);
section numbers below (§N) refer to it. Update **Current status** at the end of every
work block (§33.1).

## Current status

```text
Phase: 1 — Working VLM prototype (in progress, step 2 of 9 done).
Last completed: Phase 1 step 2 — VLM interface (backend/app/vlm/base.py), deterministic
  mock backend (mock.py), cached factory (factory.py); 81 tests passing.
Phase 1 plan (do in order, one at a time):
  1. [done] Schema v2 Pydantic models + validation tests (§7, §8 Stage C reject list)
  2. [done] Thin VLM interface + mock backend (backend/app/vlm/), single swap point (§33.3)
  3. Prompt template (§8 Stage B) with version hash; fix the diagram_type vocabulary
  4. Stage A image preprocessing (RGB, size checks, aspect-preserving resize)
  5. Hugging Face backend (Qwen3-VL via transformers, lazy imports, optional adapter).
     Cannot be run in this cloud env (huggingface.co blocked) — test what is testable
     without weights, and say so.
  6. Stage C: extract JSON from raw model text → validate → one corrective retry →
     programmatic repair (marked repaired, with a list of fixes) → structured failure;
     every outcome logged; first-attempt vs post-repair validity tracked
  7. Stage D normalization, every change logged
  8. Reproducibility metadata logging per inference call (§18.1), SQLite
  9. POST /api/analyze + frontend upload + raw output display (milestone: one image →
     valid graph JSON, including the repair path)
Next up: Phase 1 step 3 — prompt template + version hash + diagram_type vocabulary.
VLM interface decisions (Phase 1 step 2):
  - Backends implement _generate(messages, params) -> Completion; the base generate()
    validates the conversation, times the call, and returns VLMOutput carrying
    ModelInfo (backend, model_id, revision, adapter) + DecodingParams — every output is
    self-describing for §18.1 logging.
  - Input is a conversation (alternating user/assistant, starting and ending with user;
    images only on user turns, several allowed) so the Stage C retry is a follow-up turn.
  - Default decoding is greedy (temperature 0.0, top_p 1.0, max_new_tokens 4096, seed 0).
    Research runs needing variance (§20.10) must pass sampling params explicitly.
  - MockVLM returns the §7 example by default, or scripted responses in order (last one
    repeats). get_vlm_backend() is a per-process singleton (§30).
Schema decisions (Phase 1 step 1):
  - Models validate only, never mutate input (whitespace etc. is Stage D's job, logged).
  - Every node needs a non-blank label: "empty label where a visible label exists"
    (§8 C) can't be checked at runtime, so all nodes are treated as labeled.
  - node.type and edge.relation are closed enums; unknown values are rejected (repair
    may map them to "unknown", logged). Unknown keys are rejected (extra="forbid").
  - group_id must reference an existing node of type "group"; self-reference and
    containment cycles are rejected. All structural problems are reported together.
  - diagram_type is a free non-blank string for now — vocabulary TBD in step 3 (needed
    for §20.8 scoring).
  - edge.label/condition may be "" (normalization turns it into null, logged). Duplicate
    edges are not a schema error (normalization dedups, logged).
  - bbox/confidence (§7.3) are optional and omitted from output when unset.
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
