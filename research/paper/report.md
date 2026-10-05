# Vi-Graph: recovering diagram structure with a compact vision-language model

*Technical report, Phase 7 (final; draft until the OCR baseline section is filled in). Every number below was measured on the runs committed in
`evaluation/reports/` and can be recomputed from their stored predictions (§18.1); nothing is
claimed that was not measured. Scope: one synthetic benchmark. No real-diagram set was built,
and no literature review was done, so no novelty is claimed.*

## Abstract

Can a compact vision-language model (VLM) read the *structure* of a diagram, not just describe
it? We define the task as image → typed graph (nodes, labels, types, groups; directed, typed
edges), build a synthetic benchmark of 2,800 rendered diagrams with exact ground truth and a
test split with held-out layouts and themes, and evaluate with a bipartite-matching protocol
(node/edge F1, a graph-similarity score, label accuracy and a 25,698-question structural QA
benchmark). Qwen3-VL-2B-Instruct, fine-tuned with 4-bit QLoRA in 1.4 h on one GPU (peak 7.6 GB),
improves over the zero-shot model on every metric on all 500 test diagrams: graph similarity
0.581 → 0.740, edge F1 0.499 → 0.638, structural QA 0.437 → 0.582 (paired bootstrap, Holm,
p < 0.001; seed spread ≤ 0.012). Structure degrades sharply with complexity:
on the densest diagrams (25–40 nodes) graph similarity is 0.349. The dominant failure there is
*runaway enumeration*: the model keeps listing invented nodes or edges until its token budget
ends. A schema validation, retry and repair stage lifts the share of usable graphs from 73% to
91%, and a runaway guard stopping looping generations cuts evaluation time by 26% at equal
scores.

## 1. Introduction

Architecture figures, pipelines, flowcharts and UML diagrams carry their meaning in topology:
which box feeds which, where branches split and merge, what is nested in what. A caption does
not capture that; a graph does. Vi-Graph turns a diagram image into a validated, versioned graph
(schema v2), renders it as an editable diagram and as Mermaid, and answers topology questions
grounded in the graph. This report covers the research question behind it:

> How accurately can compact VLMs recover the structural relationships in visual diagrams,
> especially as diagram complexity increases?

## 2. Related work

Not surveyed for this report (§41: novelty must be established through a literature review).
The relevant areas are VLMs, document and diagram understanding, structured prediction, visual
reasoning and graph reconstruction from images.

## 3. Task

Input: one diagram image. Output: a schema-v2 JSON graph G = (V, E). Each node has an id, a
non-empty label, a type (input, output, module, operation, decision, fusion, group, unknown)
and an optional `group_id` (containment); each edge has a source, a target, a relation
(flows_to, depends_on, inherits, composes, aggregates, …) and optional label and condition. The
graph also states its diagram type (neural network, ML pipeline, flowchart, system
architecture, data pipeline, scientific workflow, UML, other). Invalid graphs (dangling edges,
unknown vocabulary, containment cycles, …) are rejected by the schema.

## 4. Dataset: synthetic-v1

A pattern-operator generator (chains, parallel branches with merges, residual and skip
connections, decisions with labeled Yes/No edges, loops, fan-in; groups up to depth 2;
long-range edges; UML inheritance and composition) produces graphs at four difficulty levels
(L1 3–6, L2 6–12, L3 12–25, L4 25–40 component nodes) and seven diagram types, rendered with
Graphviz under randomized visual themes and layout engines. 2,000 train / 300 val / 500 test,
stratified by level and type. The **test split uses layouts (layered top-to-bottom, radial,
circular) and themes (dark, blueprint, paper) never seen in training** (§16). Ground truth is
exact and independent of the renderer; manifests pin a hash of every image and graph, and every
run re-hashes its inputs. The evaluated images are the Windows build (Graphviz 16.1, test split
hash `88ae7d75…`); its ground truth is byte-identical to the committed reference build.

No real-diagram set was annotated (§15), so transfer to real diagrams is untested.

## 5. Method

**Pipeline** (the app and the evaluation run the same code):
A. preprocessing (format and size checks, aspect-preserving downscale to `image_max_side`);
B. one versioned extraction prompt (`graph_extraction@1`, hash logged);
C. JSON extraction and schema validation; on failure one corrective retry listing the problems
(including "cut off at the token limit" or "stopped because it kept repeating itself"), then a
conservative, logged repair that drops unusable parts but never invents nodes, labels or edges;
D. logged normalization (Unicode/whitespace, duplicate edges, id renumbering).
Every inference logs model + revision, adapter, prompt hashes, decoding parameters, seed,
schema version and split hash.

**Fine-tuning.** Qwen3-VL-2B-Instruct (revision `8964489`), 4-bit NF4 with double quantization,
bf16 compute; LoRA r = 16, α = 32, dropout 0.05 on the language model's attention and MLP
projections (17.4 M trainable of 2.14 B parameters; vision tower frozen). Targets are the ground
truth as compact JSON; the loss covers the answer only. 2 epochs over the 2,000 training
diagrams (250 optimizer steps, effective batch 16, lr 1e-4 cosine, paged 8-bit AdamW), images
at 896 px. One RTX A6000 with PyTorch capped at 10.5 GB: **1.4 h, peak 7.6 GB**. Train loss
0.478 → 0.069; validation loss 0.147 → 0.066.

**Runaway guard** (opt-in decoding parameter, logged). Every 16 generated tokens it checks the
text so far and stops when (1) ≥ 50 nodes are listed and the last 12 labels follow ≤ 2 templates
(numbers → `#`), (2) the last 8 edges all point to undeclared nodes, or (3) the last 12 edges
hold ≤ 4 distinct pairs. Thresholds come from train/val ground truth, on which it never fires.

## 6. Evaluation protocol

- **Matching (v1, locked):** label similarity = normalized Levenshtein on normalized labels,
  ±0.05 for agreeing/disagreeing node types, threshold 0.70; Hungarian assignment with a small
  neighbourhood tie-break; edges matched through the node assignment, each ground-truth edge
  claimed once; *strict* edge F1 also requires the relation.
- **Metrics:** node and edge precision/recall/F1; graph similarity = 1 − edit cost / (|V_p| +
  |V_g| + |E_p| + |E_g|) under that assignment (primary graph metric); label accuracy on matched
  nodes; diagram-type accuracy; validity at the first attempt and after repair; structural QA
  (successors, predecessors, sources, sinks, reachability, counts, group members, merge points;
  ~9 questions per graph, answered on the predicted graph). Failed predictions score 0.
- **Statistics:** paired bootstrap over test samples (10,000 resamples, 95% CI), Holm-adjusted
  across metrics; paired t-test and Wilcoxon reported alongside. Variance: 3 sampling seeds.
- **Protocol:** greedy decoding, 896 px, 2,048 new tokens, runaway guard on, all 500 test
  samples, one RTX 4080 SUPER for every compared run (greedy outputs are not bit-identical
  across GPU models: 49 of 112 first attempts differed between an A6000 and the 4080, with no
  metric moving by more than 0.009).

## 7. Results

### 7.1 Main result (all 500 test diagrams, greedy)

| Model (500 diagrams)  | Node F1 | Edge F1 | Strict | Graph sim. | Labels | Struct. QA | Diagram type | Valid @1 | Valid (post-repair) |
| --------------------- | ------- | ------- | ------ | ---------- | ------ | ---------- | ------------ | -------- | ------------------- |
| Qwen3-VL-2B zero-shot | 0.703   | 0.499   | 0.415  | 0.581      | 0.979  | 0.437      | 0.334        | 0.512    | 0.720               |
| Qwen3-VL-2B QLoRA     | 0.854   | 0.638   | 0.611  | 0.740      | 0.984  | 0.582      | 0.882        | 0.728    | 0.910               |

QLoRA vs zero-shot: better on every metric (p_Holm < 0.001): node F1 +0.151 [+0.122, +0.183],
edge F1 +0.139 [+0.114, +0.164], graph similarity +0.159 [+0.137, +0.181], QA +0.145, diagram
type +0.548, post-repair validity +0.190.

*(Pending: the OCR baseline on the same 500 images is still running; this is filled in when it finishes.)*

### 7.2 Run-to-run variance (3 sampling seeds, T = 0.7, top-p 0.8)

| Model     | Node F1       | Edge F1       | Graph sim.    | Struct. QA    | Valid (post-repair) |
| --------- | ------------- | ------------- | ------------- | ------------- | ------------------- |
| Zero-shot | 0.708 ± 0.012 | 0.495 ± 0.009 | 0.582 ± 0.009 | 0.441 ± 0.010 | 0.727 ± 0.012       |
| QLoRA     | 0.869 ± 0.007 | 0.639 ± 0.004 | 0.748 ± 0.006 | 0.581 ± 0.005 | 0.937 ± 0.005       |

The spread across seeds (≤ 0.012) is an order of magnitude below the fine-tuning gain, which
stays significant on every metric over seeds. Sampled QLoRA matches greedy on structure and QA;
it fails less often on L4 (26–31 failures vs 41), so its validity is 0.027 higher.

### 7.3 Complexity

Graph similarity / edge F1 by level (125 diagrams each, greedy):

| Level | QLoRA         | Zero-shot     |
| ----- | ------------- | ------------- |
| L1    | 0.961 / 0.930 | 0.875 / 0.780 |
| L2    | 0.897 / 0.817 | 0.809 / 0.721 |
| L3    | 0.754 / 0.598 | 0.552 / 0.446 |
| L4    | 0.349 / 0.208 | 0.089 / 0.051 |

Both models are near-perfect on nodes at L1–L2 and lose edges first: QLoRA node F1 falls from
1.000 to 0.503 from L1 to L4, edge F1 from 0.930 to 0.208 (H2). The fine-tuning gain is largest
on L3–L4 in absolute terms (L4 graph similarity 0.089 → 0.349).

### 7.4 Held-out layouts and diagram types

Graph similarity (QLoRA | zero-shot): circular 0.878 | 0.823 (72 diagrams), radial 0.742 |
0.580 (103), layered top-to-bottom 0.709 | 0.528 (325; training saw left-to-right). By diagram
type, QLoRA's weakest is UML (0.574, edge F1 0.406: relations drawn in UML notation); the other
six types lie between 0.743 and 0.795. Themes differ little (0.725–0.758).

### 7.5 Ablations

| Ablation (QLoRA unless noted) | Setup | Result |
| --- | --- | --- |
| Validation + retry + repair (§24D) | first attempt as-is vs final, 500 | valid 0.728 → 0.910, graph sim. 0.610 → 0.740 (zero-shot: 0.512 → 0.720, 0.414 → 0.581); all p_Holm < 0.001 |
| Output budget | 2,048 vs 4,096 tokens, 112 | identical for QLoRA (the same 14 outputs run away at both); zero-shot node F1 +0.024 |
| Image resolution (§24B) | 640 / 768 / 896 / 1024 px, 112, one GPU | 640 px worse (edge F1 −0.052 vs 896, p_Holm 0.008); 768–1024 a plateau (no significant pair); effect only on L3–L4 |
| Runaway guard | on vs off, 896 px, 112, one GPU | no metric changes (p_Holm 1.00); tokens −26%, time 1.61 → 1.19 h; outputs byte-identical wherever it did not fire |
| Hardware | same setting, A6000 vs 4080 SUPER, 112 | 49/112 first attempts differ, every metric within ±0.009 (n.s.) |

## 8. Error analysis

**§23 taxonomy** (QLoRA, greedy, over the 455 samples with a graph): per sample 3.73 missing,
3.37 wrong and 2.68 spurious edges, 2.32 omitted and 1.47 hallucinated nodes, 0.65 reversed
edges, 1.35 branch and 1.58 merge confusions, 1.94 grouping failures, 0.45 edge-label losses,
0.29 label corruptions. Edges, not labels, are the problem: label accuracy on matched nodes is
0.98–0.99 for both models. (Zero-shot counts are over its 360 graphs, which skew easier, so
totals are not comparable across models.)

**Runaway enumeration** (a failure observed beyond §23): on dense diagrams the model never closes
its JSON. It lists nodes past the real ones (“Shard 65, Shard 66, …”, “Linear 1024” repeated),
edges to node ids it never declared, or the same few edges in a loop, until the token limit.
On the 500 test diagrams the first attempt runs away on 45 of 125 L4 diagrams for QLoRA (39 stuck
in the node list) and on 108 for zero-shot. More tokens do not help (4,096 changed nothing for
QLoRA); too little resolution makes it worse (640 px), but above 768 px resolution is not its
main cause, and which diagrams run away changes with the setting. It accounts for nearly all
L4 failures (QLoRA: 41 failed of 125).

## 9. Discussion

A 2B-parameter VLM, fine-tuned for 1.4 GPU-hours on synthetic diagrams, reads small and mid-sized
diagrams reliably (graph similarity 0.96 at L1, 0.90 at L2) and generalizes to layouts and
themes it was not trained on. Its limit is scale: past ~25 nodes it loses track of what it has
already listed, which shows up as runaway enumeration rather than as gradually worse graphs.
The schema-validation and repair layer matters as much as fine-tuning for usable output (+18
points of valid graphs), and the remaining errors are structural (edges, branches, merges,
grouping), not reading errors.

## 10. Limitations

- **Synthetic only.** No real-diagram benchmark (§15), so transfer to hand-drawn, scanned or
  publication figures is unknown (H5 untested). The test split's held-out layouts and themes
  are a proxy for distribution shift, not a substitute.
- **One model family and size.** Only Qwen3-VL-2B; no larger or other VLMs (§19 B–D).
- **No perturbation study** (§22: blur, compression, occlusion, crowding) and no prompt variants
  (§24C).
- **Matching-threshold sensitivity.** Label similarity 0.70 is the spec default, not calibrated
  on real data; short labels such as “Encoder”/“Decoder” (0.714) clear it.
- **Dense layouts.** L4 remains mostly unsolved (graph similarity 0.35); runaway enumeration is
  only stopped early, not prevented.
- **OCR baseline** is a single hand-built pipeline (Tesseract + OpenCV), tuned on validation
  only; it is sensitive to rendering (§7.1).
- **Hardware non-determinism.** Greedy outputs differ across GPU models; all compared runs here
  come from one GPU, and the spread this causes is within run-to-run noise.

## 11. Conclusion

On a synthetic benchmark with held-out layouts and themes, QLoRA fine-tuning of a 2B VLM
raises structural fidelity substantially and significantly over the zero-shot model (graph
similarity 0.581 → 0.740 on 500 diagrams, seed spread ≤ 0.012). Edges
degrade faster than nodes with complexity, and on the densest diagrams the model fails by
runaway enumeration; validation and repair, and a runaway guard, make the system usable and
cheaper without changing what it gets right.

## Appendix: reproducibility

| What | Where |
| --- | --- |
| Final greedy runs (500) | `evaluation/reports/{qwen3vl-2b-qlora-a6000-v1,qwen3-vl-2b-instruct-zeroshot}-final-greedy/` |
| Seed runs (3 × 2 × 500) | `evaluation/reports/*-final-t0.7-s{0,1,2}/` |
| OCR baseline (500, same images) | `evaluation/reports/baseline-v1-final/` |
| Comparisons | `evaluation/reports/comparisons/final-greedy/`, `final-seeds/` |
| Ablation runs (112) | `evaluation/reports/qwen3vl-2b-qlora-a6000-v1-{px640,px768,px896,px1024,px896-guard,tok4096}-s0/` and comparisons |
| Training run | `training/runs/qwen3vl-2b-qlora-a6000-v1/` (config, losses, adapter config; weights kept by the author) |
| Experiment log | `research/experiment_matrix.md`, `research/error_taxonomy.md` |

Each run directory holds `run.json` (model, revision, adapter, prompt hashes, decoding
parameters, seed, split hash, GPU), `summary.json`, `report.md` and every raw model output
(`predictions.jsonl.gz`). `python -m evaluation rescore|compare|seeds` and
`evaluation/scripts/{runaway_report,repair_ablation}.py` recompute every number here from them.
