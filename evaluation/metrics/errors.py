"""Automatic error taxonomy counts for one prediction (spec §23, research/error_taxonomy.md).

Derived from the §20.1 matching. Pinned by ``scores.SCORES_VERSION``. Per sample:

- Type 1 node omission: unmatched ground-truth nodes.
- Type 2 node hallucination: unmatched predicted nodes.
- Type 3 label corruption: matched nodes whose labels differ after Stage D text
  normalization (case-sensitive).
- Edges start from the loose edge matching: unmatched predicted edges (false positives)
  and unmatched ground-truth edges (false negatives) are then explained, in this order,
  each edge used at most once:
  - Type 6 reversed edge: a false positive A→B whose endpoints are matched, where B→A is a
    false negative.
  - Type 4 wrong edge: a remaining false positive with matched endpoints that shares its
    source ("expected A→C, predicted A→B"), else its target, with a false negative.
  - Type 5 missing edge: false negatives left over.
  - Spurious edge (not a §23 type): false positives left over — usually edges touching a
    hallucinated node.
- Type 7 branch confusion: matched ground-truth forks (≥2 distinct successors) whose
  predicted successors, mapped through the assignment, differ from the ground truth's.
- Type 8 merge confusion: the same for merges (≥2 distinct predecessors) and predecessors.
- Type 10 edge-label loss: matched edges whose text was lost, changed, or hallucinated.
- Type 11 grouping failure: matched nodes in the wrong group (flattened, wrongly nested,
  or a different group).

Type 9 (layout interpretation failure) needs a human reading the image; it is not counted.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from pydantic import BaseModel

from app.pipeline.normalize import normalize_text
from app.schemas import DiagramGraph
from evaluation.metrics.matching import MatchResult

UNMATCHED = "<unmatched>"


class ErrorCounts(BaseModel):
    node_omission: int  # type 1
    node_hallucination: int  # type 2
    label_corruption: int  # type 3
    wrong_edge: int  # type 4
    missing_edge: int  # type 5
    reversed_edge: int  # type 6
    branch_confusion: int  # type 7
    merge_confusion: int  # type 8
    edge_label_loss: int  # type 10
    grouping_failure: int  # type 11
    spurious_edge: int  # false positives no type explains


def classify_errors(
    predicted: DiagramGraph,
    ground_truth: DiagramGraph,
    match: MatchResult,
    *,
    edge_text_errors: int,
    grouping_errors: int,
) -> ErrorCounts:
    """Type 10 and 11 counts come from ``scores`` (edge text and grouping scores)."""
    mapping = match.assignment
    pred_labels = {n.id: normalize_text(n.label) for n in predicted.nodes}
    gt_labels = {n.id: normalize_text(n.label) for n in ground_truth.nodes}
    label_corruption = sum(
        pred_labels[p.predicted] != gt_labels[p.ground_truth] for p in match.node_pairs
    )

    claimed_pred = {p for p, _ in match.edge_pairs}
    claimed_gt = {g for _, g in match.edge_pairs}
    # False positives with both endpoints matched, as ground-truth id pairs.
    false_positives = [
        (mapping.get(e.source), mapping.get(e.target))
        for i, e in enumerate(predicted.edges)
        if i not in claimed_pred
    ]
    false_negatives = [
        (e.source, e.target) for i, e in enumerate(ground_truth.edges) if i not in claimed_gt
    ]

    Pair = tuple[str | None, str | None]

    def take(predicate: Callable[[Pair, Pair], bool]) -> int:
        """Pair false positives with false negatives satisfying predicate; count the pairs."""
        count = 0
        for fp_index, fp in enumerate(false_positives):
            if fp is None or fp[0] is None or fp[1] is None:
                continue
            for fn_index, fn in enumerate(false_negatives):
                if fn is not None and predicate(fp, fn):
                    false_positives[fp_index] = None
                    false_negatives[fn_index] = None
                    count += 1
                    break
        return count

    reversed_edges = take(lambda fp, fn: fp == (fn[1], fn[0]))
    wrong_edges = take(lambda fp, fn: fp[0] == fn[0]) + take(lambda fp, fn: fp[1] == fn[1])

    branch, merge = _branch_and_merge_confusion(predicted, ground_truth, match)
    return ErrorCounts(
        node_omission=len(match.unmatched_ground_truth),
        node_hallucination=len(match.unmatched_predicted),
        label_corruption=label_corruption,
        wrong_edge=wrong_edges,
        missing_edge=sum(fn is not None for fn in false_negatives),
        reversed_edge=reversed_edges,
        branch_confusion=branch,
        merge_confusion=merge,
        edge_label_loss=edge_text_errors,
        grouping_failure=grouping_errors,
        spurious_edge=sum(fp is not None for fp in false_positives),
    )


def _branch_and_merge_confusion(
    predicted: DiagramGraph, ground_truth: DiagramGraph, match: MatchResult
) -> tuple[int, int]:
    mapping = match.assignment
    gt_out, gt_in = _neighbours(ground_truth, None)
    pred_out, pred_in = _neighbours(predicted, mapping)
    branch = merge = 0
    for pair in match.node_pairs:
        g, p = pair.ground_truth, pair.predicted
        if len(gt_out[g]) >= 2 and pred_out[p] != gt_out[g]:
            branch += 1
        if len(gt_in[g]) >= 2 and pred_in[p] != gt_in[g]:
            merge += 1
    return branch, merge


def _neighbours(
    graph: DiagramGraph, mapping: dict[str, str] | None
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Distinct successors and predecessors per node; ids mapped when a mapping is given."""

    def name(node_id: str) -> str:
        if mapping is None:
            return node_id
        return mapping.get(node_id, f"{UNMATCHED}:{node_id}")

    successors: dict[str, set[str]] = defaultdict(set)
    predecessors: dict[str, set[str]] = defaultdict(set)
    for edge in graph.edges:
        successors[edge.source].add(name(edge.target))
        predecessors[edge.target].add(name(edge.source))
    return successors, predecessors
