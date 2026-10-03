# Error taxonomy

Fixed taxonomy for structural failure analysis (spec §23). Every analysed failure is
assigned one or more of these types. Node-level types are derived from the node matching
in `evaluation/metrics/matching.py` (spec §20.1).

| #  | Type                          | Definition                                                                 |
| -- | ----------------------------- | -------------------------------------------------------------------------- |
| 1  | Node omission                 | A visible node is missing (unmatched ground-truth node).                   |
| 2  | Node hallucination            | A node is invented (unmatched predicted node).                             |
| 3  | Label corruption              | A matched node's label is wrong, e.g. "Multi-Head Attention" → "Multi Head Attn". |
| 4  | Wrong edge                    | Expected `A -> C`, predicted `A -> B`.                                     |
| 5  | Missing edge                  | A real connection is not predicted.                                        |
| 6  | Reversed edge                 | Expected `A -> B`, predicted `B -> A`.                                     |
| 7  | Branch confusion              | The wrong target is assigned to one branch.                                |
| 8  | Merge confusion               | The model fails to identify where branches merge.                          |
| 9  | Layout interpretation failure | The spatial arrangement is misunderstood.                                  |
| 10 | Edge-label loss               | A decision/conditional edge label ("Yes"/"No") is dropped or hallucinated. |
| 11 | Grouping failure              | A nested component loses its `group_id`, or ungrouped nodes are wrongly nested. |

## Automatic counting

`evaluation/metrics/errors.py` counts every type except 9 per prediction, from the §20.1
matching (exact definitions in its docstring; pinned by `SCORES_VERSION` in
`evaluation/metrics/scores.py`). In short: unmatched ground-truth / predicted nodes are
types 1 / 2; matched nodes with different labels are type 3; unmatched edges are explained
as reversed (6), then wrong (4: shares a source, else a target, with a missed edge), and
what is left is missing (5) or spurious (unmatched predicted edges no type explains).
Types 7 / 8 count ground-truth forks / merges whose mapped successor / predecessor set is
wrong; 10 and 11 count matched edges with wrong text and matched nodes in the wrong group.

Type 9 (layout interpretation failure) needs a human looking at the image and is assigned
manually during error analysis. Failed predictions (no graph) are counted separately, not
as omissions.

## Observed beyond §23: runaway enumeration

Found in Phase 7 ([experiment matrix](experiment_matrix.md#model-a-zero-shot-vs-qlora-vs-baseline-run-qwen3vl-2b-qlora-a6000-v1)):
on L4 diagrams the VLM keeps enumerating and never closes the JSON. It lists nodes past the
diagram's real ones, mostly invented, or emits several times the true number of edges,
until max_new_tokens runs out. The truncated JSON does not parse, and unless the Stage C retry
recovers it, the sample counts as a **failed prediction**, not as types 1–11. A larger budget
does not help: the fine-tuned model's first attempt ran away on the same 11 of 28 L4 samples at
2048 and at 4096 tokens, and 10 of the 11 failed.

It is a generation failure rather than a structural one, so it is reported next to the
taxonomy, not as a twelfth type. `evaluation/scripts/runaway_report.py` classifies each
truncated first attempt from its raw text:

| Class             | Definition                                                                 |
| ----------------- | -------------------------------------------------------------------------- |
| `stuck_in_nodes`  | The `"edges"` key never appears: the node list ran until the limit.        |
| `repeating_edges` | More duplicate (source, target) pairs than the ground truth has edges.     |
| `excess_edges`    | More than 2× the ground truth's edge count, without that many repeats.     |
| `other`           | Truncated, none of the above.                                              |

Resolution ablation (Phase 7, fine-tuned model, one GPU): runaways at L4 are 20 / 14 / 10 / 13 of
28 at 640 / 768 / 896 / 1024 px. Too little resolution makes them more frequent, but from 768 px
up a third to half of L4 still runs away, and which diagrams do so changes with the size (6 at
every size, 23 at some size), so resolution is not their main cause.

Mitigation (Phase 7, A-G in the experiment matrix): the runaway guard (`backend/app/vlm/runaway.py`)
stops a looping generation early instead of letting it run to the token limit. On the fine-tuned
model it changed no metric significantly and cut generation time by 26%; runaways are still
counted (they end with `finish_reason: "runaway"`), and they still usually fail.
