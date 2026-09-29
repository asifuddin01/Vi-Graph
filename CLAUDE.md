# CLAUDE.md — Vi-Graph

Read this first in every session. The full specification is [`docs/SPEC.md`](docs/SPEC.md);
section numbers below (§N) refer to it. Update **Current status** at the end of every
work block (§33.1).

## Current status

```text
Phase: 2 COMPLETE (milestone met: image → editable graph, with Mermaid + exports).
  Phase 3 (multimodal QA) starts next.
Last completed: Phase 2 step 4 — exports: POST /api/export (json, mermaid, svg, png, pdf)
  via Graphviz (backend/app/exporters/graphviz.py) + editor Export menu. 398 backend + 12
  frontend tests; all 5 formats verified as real downloads in Chromium.
Phase 2 plan (in order):
  1. [done] build_graph + §9 queries (predecessors/successors/sources/sinks/paths/parallel
     branches/group members/flatten) + validate_graph diagnostics
  2. [done] Mermaid generation (edge labels, subgraphs from group_id, escaping) + API field
  3. [done] React Flow editor (move/rename/add/delete nodes+edges, edge labels, types,
     group/ungroup, inspect, reset, save) + backend save endpoint
  4. [done] Exports (§28 POST /api/export: json, mermaid, svg, png, pdf)
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
  8. [done] Reproducibility metadata logging per inference call (§18.1), SQLite
  9. [done] POST /api/analyze + frontend upload + raw output display (milestone: one image →
     valid graph JSON, including the repair path)
Next up: Phase 3 — step 1 question router (§12.1, rule-based) + graph query answers.
Export decisions (Phase 2 step 4):
  - POST /api/export {format, diagram_id | graph, source: latest|original}. A posted graph
    is validated (422 lists problems) — the editor exports the canvas as-is, unsaved edits
    included. Generated filenames only; nosniff header.
  - SVG/PNG/PDF via Graphviz `dot` subprocess (no shell, 20 s timeout, ≤500 nodes). DOT ids
    generated; labels escaped incl. Graphviz's \N/\G/\n escapes — 25 adversarial labels
    verified literal in real SVG output. Groups → nested clusters; edges to a group use an
    invisible anchor + lhead/ltail. PNG at 144 dpi.
  - Graphviz is optional (§6): without `dot`, svg/png/pdf → 501; json/mermaid still work.
    Installed here via apt; backend Dockerfile installs graphviz + fonts-dejavu-core.
Editor decisions (Phase 2 step 3):
  - Edits saved via PUT /api/analyses/{id}/graph as numbered versions (graph_versions
    table, DB schema v2) + editor layout; the model's reconstruction is never overwritten.
    Responses carry the latest edit as `edited`. Phase 3 QA should answer from
    edited.graph when present.
  - frontend/lib/graph.ts (schema ⇄ React Flow, pure, tested) and lib/layout.ts (ELK
    layered, top-down, groups as nested ELK nodes; grid fallback). Group membership =
    React Flow parentId (parents ordered first). Node ids for new nodes: next n<k>.
  - React Flow defaults kept for selection: Ctrl/⌘-click multi-select, Shift-drag box.
    (Adding Shift to multiSelectionKeyCode left multi-select stuck on — don't.)
    Deleting a group deletes its contents (React Flow default; stated in the hint).
  - Frontend tests: `npm test` (vitest; config is vitest.config.mts). @types/node ^22
    (vitest 5 peer requirement; runtime is Node 22).
Mermaid decisions (Phase 2 step 2):
  - to_mermaid(graph, direction="TD"): ids n1..nk by node order; all labels quoted and
    entity-escaped (# " & < > | ; ` \ → #NN;, newlines → space). Verified with the real
    Mermaid 12 parser/renderer in Chromium via scripts/verify_mermaid/ — RE-RUN IT WHEN
    UPGRADING mermaid.
  - Shapes: input/output stadium, module/unknown rect, operation rounded, decision rhombus,
    fusion hexagon. Groups with members → nested subgraphs; empty groups → plain node.
  - Edge text = label, else condition; non-flow relations append their name ("owns
    (composes)"); depends_on is dotted. Every edge emitted (parallel edges, self-loops).
  - frontend: mermaid@12 with npm override lodash-es ^4.18.1 (mermaid 12 → chevrotain 11 →
    vulnerable lodash-es ≤4.17.23; audit's own fix was a downgrade to mermaid 11).
Graph layer decisions (Phase 2 step 1):
  - build_graph → nx.MultiDiGraph (parallel edges kept, key = edge index); node attrs
    label/type/group_id/bbox/confidence/order; all relations count for topology.
  - Outputs sorted by diagram node order (branches by flow/topological order) — deterministic.
  - Pure group containers (type group, no edges) are never sources/sinks/isolated.
  - find_parallel_branches: per fork, earliest merge points reachable from ≥2 successors;
    branch = nodes strictly between fork and merge; empty branch = skip connection;
    merge=None when branches never rejoin (then branches are each start's exclusive
    descendants).
  - validate_graph = diagnostics only (is_dag, ≤20 cycles, self loops, isolated nodes,
    weak components, sources, sinks); schema already guarantees integrity.
  - flatten_groups clears group_ids and drops pure containers; group nodes that are edge
    endpoints stay.
API decisions (Phase 1 step 9):
  - POST /api/analyze: multipart "file" (+ optional "model", must equal the served model
    id). Response = §28 shape {diagram_id, graph, mermaid (null until Phase 2), metrics,
    schema_version} + status, attempts (raw_output, problems), repairs, normalization
    changes, failure_reason, model, image. Extraction failure → 200 with status "failed".
    ImageError → 422; oversized → 413; rate limited → 429 + Retry-After; backend
    RuntimeError → 503 with a generic message (details only in server logs).
  - Limits (§29): BodySizeLimitMiddleware (Content-Length check + streaming byte count,
    max_upload_mb + 64 KiB); endpoint re-checks the file size. SlidingWindowLimiter per
    client IP (VIGRAPH_ANALYZE_RATE_LIMIT_PER_MINUTE, default 10, 0 = off).
  - Cache (§30): only with greedy decoding; key includes image_max_side (added to
    RunMetadata + DB: it is the §24B resolution variable).
  - Uploads saved as $STORAGE/images/<sha256>.<ext from detected format>; filenames ignored.
  - create_app(settings=None) so tests can configure middleware; tests override
    get_settings/get_vlm_backend/get_run_store/get_image_store/get_analyze_limiter.
Run logging decisions (Phase 1 step 8):
  - analyze_image(vlm, bytes, max_side, max_pixels, params, split_version) runs Stages A–D
    and returns AnalysisRecord(id, created_at, metadata: RunMetadata, image: ImageInfo,
    extraction, normalization, latency_ms); .graph is the normalized graph.
  - RunMetadata = the §18.1 set: app_version, schema_version, model (backend, id, resolved
    revision, adapter), DecodingParams (incl. seed), prompt + correction ids/hashes,
    split_version (None for app runs). Reused by evaluation runs later.
  - RunStore (stdlib sqlite3, WAL, connection per operation, PRAGMA user_version=1):
    reproducibility fields as columns + full record JSON. find_cached() = exact match on
    image sha, app/schema version, model, prompts, decoding params; never serves failures.
    DB path: $VIGRAPH_STORAGE_DIR/vigraph.sqlite3 (wired up in step 9).
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
  - README badges added at Phase 2 (§44.2), with Node 20.9+ (not the spec's 18+). Replace the
    "research in progress" badge with a CI build badge once CI exists.
  - frontend/app/favicon.ico is still the Next.js default.
  - Public demo: uploads/runs are kept indefinitely; add temporary storage + cleanup
    before a public deployment (§29).
  - Rate limiting is in-process (per worker); fine for a single-process demo.
  - UNVERIFIED: the backend Dockerfile's new graphviz apt layer was not built here (Docker
    Hub returned 429 rate limit for python:3.11-slim). Standard apt line; build it where
    Docker Hub is reachable.
  - Matching threshold sensitivity (§38 Limitations): edit distance rates short labels as
    close — "Encoder"/"Decoder" 0.714, "Conv 3x3"/"Conv 1x1" 0.75, "Zeta"/"Beta" 0.75 all
    clear 0.70 when types agree. Calibrate against hand-labeled real diagrams (Phase 5/7)
    and report a threshold sweep.
```

## Static conventions

- **Names:** package/repo/paths `vigraph`; display name **Vi-Graph**.
- **Schema version in effect:** `"2.0"` (§7). Pinned in `backend/app/schemas/`. Every graph
  carries `schema_version`; unknown versions are rejected.
- **Node/edge matching (§20.1) — LOCKED as matching v1** in `evaluation/metrics/matching.py`
  (`MATCHING_VERSION = "1"`; `matching_config()` reports it with library versions):
  label similarity = rapidfuzz normalized Levenshtein on NFC + whitespace-collapsed +
  casefolded labels; ±0.05 type bonus/penalty, clipped to [0, 1]; THRESHOLD 0.70 (spec
  default, not yet calibrated on real data); Hungarian assignment with a 0.01 × neighbourhood
  (pred/succ label multiset-Jaccard) tie-break — without it, a perfect prediction of a chain
  with repeated "Conv 3x3" labels scored edge F1 0.0. Edges: directed, each GT edge claimed
  once; strict variant also requires relation. Changing ANY of this = bump MATCHING_VERSION
  and record why here.
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
