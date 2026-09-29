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
