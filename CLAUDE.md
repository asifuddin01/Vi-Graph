# CLAUDE.md — Vi-Graph

Read this first in every session. The full specification is [`docs/SPEC.md`](docs/SPEC.md);
section numbers below (§N) refer to it. Update **Current status** at the end of every
work block (§33.1).

## Current status

```text
Phase: 1 — Working VLM prototype (in progress, step 7 of 9 done).
Last completed: Phase 1 step 7 — Stage D normalization (backend/app/pipeline/normalize.py);
  239 tests passing.
Phase 1 plan (do in order, one at a time):
  1. [done] Schema v2 Pydantic models + validation tests (§7, §8 Stage C reject list)
  2. [done] Thin VLM interface + mock backend (backend/app/vlm/), single swap point (§33.3)
  3. [done] Prompt template (§8 Stage B) with version hash; diagram_type vocabulary
  4. [done] Stage A image preprocessing (RGB, size checks, aspect-preserving resize)
  5. [done] Hugging Face backend (Qwen3-VL via transformers, lazy imports, optional
     adapter). NOT run against real weights (see Known issues).
  6. [done] Stage C: extract JSON from raw model text → validate → one corrective retry →
     programmatic repair (marked repaired, with a list of fixes) → structured failure;
     every outcome logged; first-attempt vs post-repair validity tracked
  7. [done] Stage D normalization, every change logged
  8. Reproducibility metadata logging per inference call (§18.1), SQLite
  9. POST /api/analyze + frontend upload + raw output display (milestone: one image →
     valid graph JSON, including the repair path)
Next up: Phase 1 step 8 — reproducibility logging (SQLite).
Stage D decisions (Phase 1 step 7):
  - normalize_graph(validated graph) → NormalizationResult(graph, changes, id_map).
  - Text: NFC + whitespace collapse for node labels, edge labels, conditions; blank edge
    text → null. Exact duplicate edges removed (first kept).
  - Node ids renumbered n1..nk in node order when not already; id_map covers every node.
  - Duplicate labels flagged only (never merged). Edge direction and relations untouched
    (vocabulary has no inverse forms; topology preserved exactly).
Stage C decisions (Phase 1 step 6):
  - extract_graph(vlm, images, params) → ExtractionResult with status
    valid_first_attempt | valid_after_retry | repaired | failed, every Attempt (raw output,
    json_method, problems), repairs, repaired_from_attempt, failure_reason, prompt ids+hashes.
    §20.2 first-attempt validity = status == valid_first_attempt; post-repair = != failed.
  - JSON extraction order: direct → fenced → embedded; method recorded (a stricter
    "bare JSON" validity can be computed from json_method == "direct").
  - One retry: [user prompt+image, assistant raw output, user graph_correction@1 listing
    ≤20 problems]. Same DecodingParams. Truncation (finish_reason=length) is reported first.
  - Repair runs on attempt 2, else attempt 1 (whichever parsed). Conservative: drops
    unusable nodes/edges/fields, maps case/spacing variants of vocabulary values, defaults
    unknown values to unknown/other, retypes non-group containers to group, breaks group
    cycles at the first node, never invents nodes/labels/edges. Each fix = RepairCode +
    message. Empty result or non-list nodes → failed.
  - Schema raises GraphStructureError(problems) so problems are listed without parsing text.
HF backend decisions (Phase 1 step 5):
  - Generic AutoModelForImageTextToText + AutoProcessor.apply_chat_template, so any HF
    VLM works (§19). Checked against transformers 5.17 source (dtype= kwarg, image
    content blocks {"type": "image", "image": PIL}, generate kwarg precedence).
  - DecodingParams fully determine decoding: repetition_penalty forced to 1.0, and when
    sampling top_k=0 — model generation_config defaults can't silently apply.
  - Weights load lazily on first generate (or .load()); one generation at a time (lock).
  - Logged revision = resolved commit hash (config._commit_hash) when available.
  - finish_reason "length" when completion_tokens >= max_new_tokens.
  - Visual-token budget is controlled via VIGRAPH_IMAGE_MAX_SIDE (Stage A), not
    processor-specific kwargs.
Preprocessing decisions (Phase 1 step 4):
  - Accepted formats: PNG, JPEG, WebP, detected from content. Rejected: everything else
    (incl. GIF, BMP, TIFF, SVG, PDF).
  - Pixel limit (VIGRAPH_IMAGE_MAX_PIXELS, 40M) is checked from the header before decoding.
  - EXIF orientation applied; transparency flattened onto white (not black).
  - Downscale only when longest side > VIGRAPH_IMAGE_MAX_SIDE (2048), LANCZOS, aspect kept;
    never upscale. The model's own processor applies its pixel budget on top (step 5).
  - sha256 of original bytes kept for caching/logging.
  - Deferred: the optional high-res crop for dense diagrams (§8 A.6).
Prompt decisions (Phase 1 step 3):
  - Prompts are PromptTemplate(name, version, text); id "name@version"; sha256 of the exact
    text is logged. Editing a prompt requires bumping its version and the pinned hash.
  - graph_extraction@1 = spec §8 Stage B text, allowed values filled from the schema enums,
    plus two added requirements the schema enforces: non-empty node labels, and containers
    must have type "group".
  - diagram_type vocabulary (closed enum): neural_network, ml_pipeline, flowchart,
    system_architecture, data_pipeline, scientific_workflow, uml, other (from spec §1).
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
  - UNVERIFIED: the hf backend has never run against real weights (huggingface.co and
    download.pytorch.org are blocked here; torch not installed). Verify where HF is
    reachable: `pip install -r requirements-vlm.txt`, then from backend/
    `VIGRAPH_VLM_BACKEND=hf VIGRAPH_VLM_DTYPE=float16 python -m app.vlm some_diagram.png`.
    Also unverified: Qwen3-VL numerical stability in float16 on T4.
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
