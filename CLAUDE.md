# CLAUDE.md — Vi-Graph

Read this first in every session. The full specification is [`docs/SPEC.md`](docs/SPEC.md);
section numbers below (§N) refer to it. Update **Current status** at the end of every
work block (§33.1).

## Current status

```text
Phase: 7 — Research experiments (next). Phases 1–6 complete: usable product, synthetic
  dataset, evaluation framework + classical baseline, first QLoRA run trained and evaluated
  (on the user's RTX A6000; results in research/experiment_matrix.md).
Last completed: Phase 6 hand-back processed — run qwen3vl-2b-qlora-a6000-v1: 24/24 files
  sha256-verified (adapter weights kept by the user; sha256 in
  training/runs/<run>/handback_MANIFEST.json), all 336 predictions re-scored here → identical;
  715 tests passing.
Phase 7 plan (first steps; GPU steps run on the user's PC via the Windows notebook):
  1. Re-evaluate zero-shot + QLoRA with max_new_tokens 4096 (app default) — L4 was
     truncation-bound at 2048 (zero-shot 27/28, QLoRA 11/28 truncated)
  2. Full 500-sample test + 3 seeds (sampling) for variance (§20.10)
  3. Perturbation study (§22), resolution ablation (§24B), repair ablation (§24D, data
     already logged as first-attempt scores), real-diagram set (§15)
Phase 6 plan (done, in order):
  1. [done] Config (training/configs/qlora_t4.yaml), examples = inference conversation +
     compact GT JSON, loss masking through the template's assistant header
  2. [done] Trainer (4-bit NF4, LoRA, HF Trainer, Drive checkpoints + resume guard,
     §18.1 training_run.json) + hand-back zip with MANIFEST.json
  3. [done] Notebook in the user's section order: setup → dataset → preprocess → model
     (smoke run) → train (resumable) → evaluation (resumable) → save & hand back
Phase 5 plan (in order):
  1. [done] Per-sample scores v1: validity (first-attempt, bare JSON, post-repair), node/edge
     P/R/F1 (loose/strict), graph similarity, label accuracy/CER/WER, edge text,
     grouping, diagram type; automatic §23 taxonomy (all types but 9)
  2. [done] Structural QA benchmark (§20.7): questions generated from the ground truth,
     answered on the predicted graph
  3. [done] Evaluation runner: dataset split → pipeline (any VLM backend) → predictions +
     per-sample scores → run directory with §18.1 metadata + split hash; resumable
     (Colab); aggregates (macro + micro; by level / diagram type / layout), latency
  4. [done] Seeds + significance (§20.10–20.11): mean ± std across runs, paired bootstrap +
     paired t-test / Wilcoxon on per-sample scores, compare CLI, markdown report
  5. [done] Non-VLM baseline (§19.1, §42 item 10): OCR + OpenCV geometry → graph, scored
     by the same runner; one run on synthetic-v1 test (research/experiment_matrix.md)
Phase 6 (Colab hand-off) — USER PREFERENCE (stated during Phase 4; delivered): .ipynb, one
  notebook split into clearly separated sections, each with its own purpose, in order:
  library install/import → dataset import (build in Colab, verify against the committed
  manifest) → preprocess → model load → train (resumable after interruption:
  checkpoints on Drive, auto-resume) → evaluation → save, ending with the exact list of
  files the user should give back to Claude (adapter, eval reports, run metadata, logs).
Phase 4 plan (in order):
  1. [done] Pattern-operator graph generator, difficulty L1–L4, 7 diagram types, spec per
     sample (patterns, sizes, depth, cycles, groups)
  2. [done] Renderer: Graphviz with randomized visual themes + layout families
     (layered_tb, layered_lr, radial, circular, force)
  3. [done] Dataset builder CLI (build/verify/stats): images + GT JSON + metadata.jsonl,
     stratified splits with held-out layouts/themes for test (§16), split hashes
     (§18.1); committed manifest/stats in data/splits/, 8 examples in examples/
Phase 3 plan (in order):
  1. [done] Rule-based router (§12.1) + entity linking + grounded graph answers
  2. [done] VLM path for visual / "why" / unknown questions (versioned QA prompt, image from the
     ImageStore) + POST /api/qa + qa log (routing decision logged, §28)
  3. [done] Frontend: question box + §26 quick buttons (Explain / Find branches / Analyze
     topology) + highlight grounded nodes/edges in the editor
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
Next up: Phase 7 step 1 (re-evaluation with max_new_tokens 4096).
Results decisions (hand-back of qwen3vl-2b-qlora-a6000-v1):
  - Committed: evaluation/reports/{qwen3-vl-2b-instruct-zeroshot-s0, qwen3vl-2b-qlora-a6000-v1-s0,
    baseline-v1-windows}/ (run.json, summary.json, report.md, predictions.jsonl.gz),
    evaluation/reports/comparisons/qwen3vl-2b-qlora-a6000-v1/, training/runs/<run>/
    (training_run.json, run_config.json, train_log.jsonl, adapter_config.json,
    memory_probe.json, handback_MANIFEST.json), data/splits/synthetic-v1.windows-graphviz16
    .manifest.json (the eval data build: Graphviz 16.1, ground truth identical).
  - Training: bf16, image_max_side 896 (probe at the 10.5 GB cap: 1024 peaked 9.91 GB > 9.45 GB
    budget), 250 steps, 1.36 h, peak 7.6 GB allocated / 9.3 GB reserved (probe). Loss
    0.478 → 0.069, val 0.147 → 0.066. The user asked to highlight the lightweight run: stated
    in README as MEASURED peak memory (7.6 GB), not the cap (10.5 GB).
  - Eval (112-sample stratified test prefix, greedy, 2048 tokens, 896 px): QLoRA > zero-shot on
    all 9 metrics (significant); QLoRA ≈ baseline on node/edge/graph similarity (n.s.), better
    on labels/QA/type; zero-shot < baseline on structure. git_commit is null in these runs
    (the Windows notebook downloads the code as a zip); code was 57a2f55 or later.
Windows notebook (training/notebooks/vigraph_qlora_windows.ipynb, hand-maintained — the user
  moved from Colab to a Windows PC with an RTX A6000; F:\vigraph, venv, bf16, a driver
  script it writes to tools/vigraph_windows.py applies the VRAM cap, Linux-identical file
  writes and no DataLoader workers):
  - First run failed in section 3: the memory probe (section 4, run earlier) found no image
    size under 90 % of a 9.5 GB cap (peaks 8.66–9.29 GB for 1024…640 — memory is dominated
    by the text/vocab side, not the image) and wrote chosen_image_max_side: null;
    image_side() passed that null into every config → pydantic int error.
  - Fix (user asked for a 10–11 GB cap): VRAM_LIMIT_GB 10.5 (≈ 11 GB in nvidia-smi with
    the CUDA context; budget 9.45 GB → 1024 fits); image_side() returns 1024 before the
    probe and raises a clear "raise VRAM_LIMIT_GB" error instead of returning null;
    section 3 uses overrides(with_image_side=False). training/tests/test_windows_notebook.py.
Training decisions (Phase 6):
  - UNVERIFIED on a GPU: nothing in training/ has run against real weights or CUDA here
    (huggingface.co / torch blocked). APIs were checked against transformers 5.17.0, peft
    0.21.1, accelerate 1.15.0, bitsandbytes 0.50.2 source: TrainingArguments has no
    warmup_ratio in v5 (warmup_steps takes a ratio), processor returns mm_token_type_ids
    (forward accepts it), Qwen3-VL vision modules are qkv/proj/linear_fc*, LM modules
    q/k/v/o_proj + gate/up/down_proj. The notebook's smoke run (section 4) exists to catch
    what source reading can't, before hours of training.
  - Targets: compact JSON, nulls omitted (mean ~650 tokens, max ~1.8k on synthetic-v1
    train). Loss only on the answer + end-of-turn; header derived from the template
    (with_prompt minus without), found by last occurrence; the notebook asserts the trained
    text starts with {"schema_version":"2.0".
  - micro-batch 1 (variable image sizes); prepare_model_for_kbit_training with
    non-reentrant checkpointing; use_cache off; fp16 (T4).
  - Colab install (fixed after the user's first run): requirements-train.txt must NOT
    `-r requirements.txt` — its numpy>=2.4 upgraded Colab's numpy 2.2 → 2.5.3 (breaks
    numba; mixed versions in a live session). It now lists only what training/eval need,
    with no bounds on numpy/scipy/pillow/torch, and the install cell pins Colab's
    numpy/scipy/pillow/torch(+vision/audio) via `pip freeze` → `-c` constraints. Test
    guards both. Colab (Ubuntu 24.04) ships Graphviz 2.43.0 — same as the committed build.
  - Resume: run_config.json = config + split infos (minus directory); mismatch refuses.
    The notebook's train cell skips when training_run.json + adapter exist.
  - Evaluation in Colab: zero-shot, fine-tuned and baseline on the SAME Colab data build and
    the same EVAL_LIMIT (default 112 = 4 × 28 stratified prefix) so comparisons are paired;
    greedy, max_new_tokens 2048, image_max_side 1024 (= training).
  - Notebook generated by training/notebooks/make_notebook.py (tests: matches generator,
    section order, every code cell parses); *.ipynb excluded from ruff.
Baseline decisions (Phase 5 step 5):
  - evaluation/baseline/, BASELINE_VERSION = "1". Generic: no generator themes, fonts or
    vocabularies (only a short domain-keyword list to guess diagram_type).
  - Ink = |gray − medianBlur(gray, 21)| > 50 (thin structures; fills of any colour are not
    ink — a plain grey threshold failed on saturated fills). Nodes = enclosed background
    regions with ink inside. Filled groups = painted mask (any channel > 4 from the
    background) eroded 3 px, enclosing shapes with ≥ 6 px margin; interior pieces cut by
    edges are dropped. Types: diamond → decision, hexagon → fusion, sources → input, sinks →
    output, else module; relation always flows_to.
  - OCR per shape: crop, mask outside the shape, normalize polarity, scale letters to
    ~25 px, psm 6 (whole-page OCR was unreliable next to box outlines). Group label: top
    band (2.5 × text height), band-spanning strokes removed, top row joined. One sparse
    pass for free text (conf ≥ 60) → label of the nearest edge.
  - Edges: strokes minus shapes (dilated) and text; per stroke, ends at nodes with ≥ 1.5×
    the thinnest end's ink are arrowheads; no arrowhead → left→right / top→bottom.
  - Tuned on val only (ink window 9 → 21 doubled edge F1; head ratio flat). Tried and
    rejected: closing dashed borders (node F1 0.88 → 0.67), dropping long strokes before
    free-text OCR (lost labels). Known limitations: dashed group borders, text touching or
    crossed by strokes, ~5 px text, UML relation types.
  - val (56 samples): node F1 0.866, edge F1 0.617, graph similarity 0.726.
  - test (500, one run at commit f5849dd, ~3 s/sample): node F1 0.931, edge F1 0.635,
    strict 0.584, graph sim 0.781, labels 0.960, QA 0.462. Higher than val (node F1
    0.866): val's wide layered_lr L4 renders shrink text to ~5 px (seen on val-000015);
    by layout on test, circular is its best (edge F1 0.828) and radial its worst (0.344).
  - The test run was interrupted at 107/500 and resumed (moved out of the repo) — the
    resume path worked on a real interruption.
Statistics decisions (Phase 5 step 4):
  - Primary significance test (§20.11, documented in evaluation/stats.py): paired
    bootstrap over test samples, 10,000 resamples (seed 0), 95% percentile CI of the mean
    difference, two-sided null-centered p with +1 correction; Holm–Bonferroni across the
    metrics in one comparison. Paired t-test + Wilcoxon reported alongside.
  - Multi-seed conditions: per-sample value = mean over the condition's runs, then paired.
    seeds = mean ± std of per-run macro means, overall and per level; refuses runs that
    differ in anything but seed. Both require identical split hash + sample ids.
Runner decisions (Phase 5 step 3):
  - Evaluation runs the app's own pipeline (analyze_image, Stages A–D) — scores are of the
    system users get. Predictor ABC (VLMPredictor, OraclePredictor; the step-5 baseline
    plugs in here). Oracle = ground truth through the full pipeline: must score 1.000
    (verified on all 500 synthetic-v1 test samples).
  - load_split re-hashes every image/GT file and checks the manifest split hash before a
    run; RunMetadata.split_version = split hash.
  - Per sample: prediction (AnalysisRecord with every raw attempt), scores, first-attempt
    scores (attempt 1 as-is: no retry/repair/normalization — ablation §24D / H4), QA.
  - Resumable: predictions.jsonl appended + fsynced per sample; torn last line dropped;
    same RunConfig + same split hash required; predictor exceptions recorded as failures
    (error field), --retry-errors re-runs them; 3 consecutive errors abort.
  - Headline = macro mean over samples (failures = 0, undefined metrics skipped, n shown);
    pooled micro numbers alongside. Breakdowns by level/diagram type/layout/theme.
  - Committed per run: run.json, summary.json, report.md, predictions.jsonl.gz (~0.5 MB
    per 500 samples); predictions.jsonl is gitignored.
Structural QA decisions (Phase 5 step 2):
  - QA_BENCHMARK_VERSION = "1" (evaluation/metrics/structural_qa.py; definition in its
    docstring). ≤1 question per kind per graph, seeded by sample id, only about nodes with
    unique labels: successors, predecessors, sources, sinks, path_exists (one reachable,
    one unreachable), count_nodes (non-group), count_edges, group_members, merge_point.
    synthetic-v1: 25,698 questions (~9 per graph).
  - Answers computed with app.graph topology functions; entities resolved and answer nodes
    mapped through the §20.1 assignment (structure only — labels are scored elsewhere);
    exact equality of GT-id sets / bool / int (bool never equals a count).
  - Each question has NL text + the router intent it is phrased for (for a later
    end-to-end QA eval); all 25,698 route correctly.
  - Router/engine fixes found by it (Phase 3 code): "inputs of the diagram" → sources (was
    predecessors); count_edges before neighbors ("How many connections…"); the engine
    routes with named nodes masked (route_with_mentions) so label words can't pick the
    intent — one-word keyword labels ("Merge") stay words after a named node or plural
    subject; falls back to the unmasked question if masked is unknown. Entity linking:
    a fuzzy match loses to an exact match of another label on the same words
    ("Transform" ≠ "Transform 2"). Routing on the benchmark: 25,076 → 25,698 / 25,698.
Scores decisions (Phase 5 step 1):
  - SCORES_VERSION = "1" in evaluation/metrics/scores.py pins every definition (full text in
    its docstring); changing one = bump + record here. Built on matching v1 (unchanged;
    MatchResult gained edge_pairs = claimed (pred, gt) edge indices, additive).
  - Primary graph metric (§20.5) = graph similarity: 1 − cost / (|V_p|+|V_g|+|E_p|+|E_g|),
    cost = edit cost under the §20.1 assignment (1 per unmatched node/edge, 1 − pair
    similarity per matched node, 1 per matched edge with a different relation). Upper
    bound on exact GED with these costs (tested against networkx GED); exact GED is
    intractable at 40 nodes. Edge text and grouping scored separately, not in it.
  - Failed predictions score as empty: F1 0, similarity 0, type wrong; label/edge-text/
    grouping undefined, taxonomy not computed (failures counted separately).
  - Labels: Stage D text normalization, case-sensitive exact + casefold exact, normalized
    Levenshtein, pooled CER/WER. Edge text = label else condition, casefolded.
  - Taxonomy (errors.py): unmatched edges explained reversed → wrong (same source, then
    same target) → missing / spurious. Forks/merges: ≥2 distinct successors/predecessors.
  - Sanity: all 2,800 synthetic-v1 GT graphs self-score perfectly; ~3 ms/sample.
Dataset decisions (Phase 4 step 3):
  - synthetic-v1 = seed 0, 2000 train / 300 val / 500 test (§32). Stratified: levels cycle
    fastest, then diagram types. Per-sample seed "{seed}:{split}:{index}".
  - Held-out test (§16): train/val use layered_lr + force and themes classic, pastel,
    corporate, vivid, sketch; test uses layered_tb, radial, circular and themes dark,
    blueprint, paper. Optional --iid-test split to measure the shift.
  - Manifest pins split_hashes (ids + image + GT hashes; the §18.1 split version) and
    graph_hashes (ids + GT only). Images depend on the Graphviz version; GT must not —
    `verify --reference data/splits/synthetic-v1.manifest.json` checks rebuilds (Colab).
  - Committed build: Graphviz 2.43.0, dataset hash 6edd5f63…32e6 (identical across
    rebuilds and thread counts). Datasets themselves are gitignored (data/synthetic/).
  - Determinism: fdp is not reproducible (esp. with clusters), neato with overlap=false
    neither → force layout = neato, start=<layout_seed>, overlap=scale.
Renderer decisions (Phase 4 step 2):
  - Themes: classic, pastel, dark, blueprint, sketch, corporate, paper, vivid. Layouts:
    layered_tb/layered_lr (dot), radial (twopi), circular (circo), force (neato; was fdp,
    changed in step 3 for determinism).
  - Faithfulness rules: graphs with groups only get cluster layouts (dot, CLUSTER_LAYOUTS);
    graphs with edge labels never get splines=ortho (can drop labels); decisions are
    always diamonds; UML relations drawn in UML notation; depends_on dashed.
  - Font size by level (L1 14–18 pt … L4 7–10 pt); denser spacing at L3+; size ≤16 in.
  - DejaVu fonts only; RenderParams + graphviz_version() recorded for exact re-rendering.
  - Deferred: node bboxes (§7.3 optional) — Graphviz scaling makes pixel-exact boxes
    fiddly; not needed for MVP.
Generator decisions (Phase 4 step 1):
  - Code in data/generator/ (package `data`, importable from repo root; tests in data/tests).
    GENERATOR_VERSION = "1" — bump when output for a seed changes.
  - Levels (component nodes): L1 3–6, L2 6–12, L3 12–25, L4 25–40 (spec: "25+", capped for
    legibility). Node budget fixed up front, so counts always land in range.
  - Operators: chain, parallel (branch+merge, multi-branch at L3+), residual (+Add),
    skip, decision (Yes/No labeled edges → join), loop (cycle via "No" back edge, L3+),
    fan_in; passes: groups (L2+, nested depth 2 at L3+), long-range edge (L3+), edge
    labels (L3+ pipelines/systems), depends_on (system architecture). UML: inheritance
    forest + composes/aggregates/depends_on.
  - L1–L2 are acyclic, L1 has no groups. Repeated labels only in neural networks (L2+).
  - GT relations are visually grounded: plain arrows = flows_to (decision branches carry
    Yes/No as edge.label, not a special relation).
QA UI decisions (Phase 3 step 3):
  - QAPanel above the Mermaid view; answers newest first with source badge and
    route; clicking an answer toggles highlighting of its grounding.
  - Highlighting is derived at render time (useMemo className on nodes/edges) — never
    written into editor state, so it can't mark the graph dirty.
  - Answers use the last *saved* graph (stated in the UI); unsaved edits aren't seen.
QA engine/API decisions (Phase 3 step 2):
  - Graph answers first; VLM only when the route needs the image (visual, "why") or the
    graph can't answer (unknown intent / no graph). "why" = graph part + VLM reason.
  - The mock backend is never used to answer questions (it only emits canned graph JSON);
    in mock mode the answer says a vision model is needed. Tests use tests/vlm_doubles.py.
  - visual_qa@1 prompt: image + compact graph JSON + question, 1–3 sentences, say so if
    the image doesn't show it. QA decoding: max_new_tokens 256, greedy.
  - QA answers from the latest saved edit (graph_version in the response), else original.
    Stored upload is re-preprocessed only when the question can use the image.
  - Every question logged in qa_log (route incl. matched rule, mentions, source,
    grounding, VLM output). Separate rate limit VIGRAPH_QA_RATE_LIMIT_PER_MINUTE (30).
QA decisions (Phase 3 step 1):
  - route_question → Route(category, intent, rule). Categories: direct, structural,
    comparative, explanation (graph-only); visual (VLM); mixed = "why" (graph part +
    image); unknown. Ordered regex rules, first match wins — order matters (visual first,
    specific before generic, "feeds into X" before "input").
  - Entities: exact normalized label on word boundaries; fuzzy only for labels ≥6 chars,
    rapidfuzz ratio ≥88 over whole-word windows; node ids ("n3"); generic "the input" /
    "the output" → sources/sinks only when nothing is named. Longest span wins overlaps;
    repeated labels return every node; question order kept (paths from A to B).
  - answer_from_graph(intent, …) → GraphAnswer(text, grounding{nodes, edges}, complete).
    complete=False only for "why" (graph says that, not why). Shared labels are shown
    with their id, e.g. "Conv 3x3 (c1)". Node-needing intents without a node ask which.
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
