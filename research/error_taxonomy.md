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
