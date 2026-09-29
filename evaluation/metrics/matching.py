"""Node/edge matching between a predicted and a ground-truth graph (spec §20.1).

Every metric in evaluation/ depends on this. ``MATCHING_VERSION`` pins the definition
below; changing any constant or step is a versioned decision — bump the version and record
why in CLAUDE.md. ``matching_config()`` returns the full definition, including library
versions, for run reports (§18.1).

Definition, matching v1:

1. Label similarity = normalized Levenshtein similarity, 1 - lev(a, b) / max(len(a), len(b))
   (``rapidfuzz.distance.Levenshtein.normalized_similarity``), on labels that are
   NFC-normalized, whitespace-collapsed, and casefolded.
2. Pair similarity = label similarity + TYPE_BONUS if node types are equal, else
   - TYPE_PENALTY; clipped to [0, 1].
3. Pairs with similarity < THRESHOLD can never match.
4. A 1-to-1 assignment maximizing total weight is found with the Hungarian algorithm
   (``scipy.optimize.linear_sum_assignment``). Weight = similarity + CONTEXT_WEIGHT x
   neighbourhood similarity (mean multiset-Jaccard of predecessor labels and of successor
   labels). The context term only breaks ties between near-identical labels, such as
   repeated "Conv 3x3" blocks; it never decides whether a pair clears the threshold.
5. Matched pairs are true positives. Unmatched predicted nodes are false positives
   (possible hallucination, §23 type 2); unmatched ground-truth nodes are false negatives
   (possible omission, type 1).
6. Edges: each predicted edge (s, t) is mapped through the node assignment; it is a true
   positive if the mapped directed edge exists in the ground truth and has not already been
   claimed. The strict variant also requires the relation to be equal. Edges touching an
   unmatched node are false positives.

Zero-division convention: precision (recall) is 1.0 when there are no predictions (ground
truth items) and nothing was missed (hallucinated), else 0.0.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from importlib.metadata import version

import numpy as np
from pydantic import BaseModel
from rapidfuzz.distance import Levenshtein
from rapidfuzz.process import cdist
from scipy.optimize import linear_sum_assignment

from app.pipeline.normalize import normalize_text
from app.schemas import DiagramGraph

MATCHING_VERSION = "1"
THRESHOLD = 0.70
TYPE_BONUS = 0.05
TYPE_PENALTY = 0.05
CONTEXT_WEIGHT = 0.01


class PRF(BaseModel):
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float


class NodePair(BaseModel):
    predicted: str
    ground_truth: str
    similarity: float
    label_similarity: float


class EdgeKey(BaseModel):
    source: str
    target: str
    relation: str


class MatchResult(BaseModel):
    matching_version: str
    node_pairs: list[NodePair]
    unmatched_predicted: list[str]
    unmatched_ground_truth: list[str]
    nodes: PRF
    edges: PRF
    edges_strict: PRF  # relation must match as well
    # Loose-variant edge outcomes, for error analysis (§23). True/false positives use
    # predicted ids; false negatives use ground-truth ids.
    edge_true_positives: list[EdgeKey]
    edge_false_positives: list[EdgeKey]
    edge_false_negatives: list[EdgeKey]

    @property
    def assignment(self) -> dict[str, str]:
        """Predicted node id → matched ground-truth node id."""
        return {pair.predicted: pair.ground_truth for pair in self.node_pairs}


def matching_config() -> dict[str, object]:
    return {
        "matching_version": MATCHING_VERSION,
        "label_similarity": "rapidfuzz Levenshtein.normalized_similarity on NFC, "
        "whitespace-collapsed, casefolded labels",
        "threshold": THRESHOLD,
        "type_bonus": TYPE_BONUS,
        "type_penalty": TYPE_PENALTY,
        "context_weight": CONTEXT_WEIGHT,
        "rapidfuzz_version": version("rapidfuzz"),
        "scipy_version": version("scipy"),
    }


def prf(tp: int, fp: int, fn: int) -> PRF:
    precision = tp / (tp + fp) if tp + fp else (1.0 if fn == 0 else 0.0)
    recall = tp / (tp + fn) if tp + fn else (1.0 if fp == 0 else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PRF(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall, f1=f1)


def matching_label(label: str) -> str:
    return normalize_text(label).casefold()


def assign(
    similarity: np.ndarray, weight: np.ndarray, threshold: float = THRESHOLD
) -> list[tuple[int, int]]:
    """Max-weight 1-to-1 assignment among pairs with similarity >= threshold.

    Ineligible pairs get weight 0, and zero-weight picks are dropped afterwards, so the
    result is a maximum-weight matching restricted to eligible pairs.
    """
    if similarity.size == 0:
        return []
    eligible = similarity >= threshold
    rows, cols = linear_sum_assignment(np.where(eligible, weight, 0.0), maximize=True)
    return [(int(r), int(c)) for r, c in zip(rows, cols, strict=True) if eligible[r, c]]


def match_graphs(predicted: DiagramGraph, ground_truth: DiagramGraph) -> MatchResult:
    pred_nodes, gt_nodes = predicted.nodes, ground_truth.nodes

    label_sim = cdist(
        [matching_label(n.label) for n in pred_nodes],
        [matching_label(n.label) for n in gt_nodes],
        scorer=Levenshtein.normalized_similarity,
        dtype=np.float64,
    )
    same_type = np.array([[p.type == g.type for g in gt_nodes] for p in pred_nodes], dtype=bool)
    similarity = np.clip(label_sim + np.where(same_type, TYPE_BONUS, -TYPE_PENALTY), 0.0, 1.0)

    pred_context = _neighbourhoods(predicted)
    gt_context = _neighbourhoods(ground_truth)
    context = np.array(
        [
            [_context_similarity(pred_context[p.id], gt_context[g.id]) for g in gt_nodes]
            for p in pred_nodes
        ]
    )

    pairs = assign(similarity, similarity + CONTEXT_WEIGHT * context)
    node_pairs = [
        NodePair(
            predicted=pred_nodes[r].id,
            ground_truth=gt_nodes[c].id,
            similarity=float(similarity[r, c]),
            label_similarity=float(label_sim[r, c]),
        )
        for r, c in pairs
    ]
    matched_pred = {pair.predicted for pair in node_pairs}
    matched_gt = {pair.ground_truth for pair in node_pairs}
    unmatched_pred = [n.id for n in pred_nodes if n.id not in matched_pred]
    unmatched_gt = [n.id for n in gt_nodes if n.id not in matched_gt]
    mapping = {pair.predicted: pair.ground_truth for pair in node_pairs}

    loose = _score_edges(predicted, ground_truth, mapping, strict=False)
    strict = _score_edges(predicted, ground_truth, mapping, strict=True)

    return MatchResult(
        matching_version=MATCHING_VERSION,
        node_pairs=node_pairs,
        unmatched_predicted=unmatched_pred,
        unmatched_ground_truth=unmatched_gt,
        nodes=prf(len(node_pairs), len(unmatched_pred), len(unmatched_gt)),
        edges=loose.prf,
        edges_strict=strict.prf,
        edge_true_positives=loose.true_positives,
        edge_false_positives=loose.false_positives,
        edge_false_negatives=loose.false_negatives,
    )


class _EdgeScore(BaseModel):
    prf: PRF
    true_positives: list[EdgeKey]
    false_positives: list[EdgeKey]
    false_negatives: list[EdgeKey]


def _score_edges(
    predicted: DiagramGraph, ground_truth: DiagramGraph, mapping: dict[str, str], *, strict: bool
) -> _EdgeScore:
    def key(source: str, target: str, relation: str) -> tuple[str, ...]:
        return (source, target, relation) if strict else (source, target)

    # A list per key: in the loose variant, two ground-truth edges between the same nodes
    # with different relations share a key, and each can be claimed once.
    unclaimed: dict[tuple[str, ...], list[EdgeKey]] = defaultdict(list)
    for e in ground_truth.edges:
        unclaimed[key(e.source, e.target, e.relation)].append(
            EdgeKey(source=e.source, target=e.target, relation=e.relation)
        )
    true_positives: list[EdgeKey] = []
    false_positives: list[EdgeKey] = []
    for edge in predicted.edges:
        as_key = EdgeKey(source=edge.source, target=edge.target, relation=edge.relation)
        if edge.source in mapping and edge.target in mapping:
            bucket = unclaimed.get(key(mapping[edge.source], mapping[edge.target], edge.relation))
            if bucket:
                bucket.pop(0)
                true_positives.append(as_key)
                continue
        false_positives.append(as_key)
    false_negatives = [edge for bucket in unclaimed.values() for edge in bucket]
    return _EdgeScore(
        prf=prf(len(true_positives), len(false_positives), len(false_negatives)),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )


_Context = tuple[Counter[str], Counter[str]]  # (predecessor labels, successor labels)


def _neighbourhoods(graph: DiagramGraph) -> dict[str, _Context]:
    labels = {node.id: matching_label(node.label) for node in graph.nodes}
    predecessors: dict[str, Counter[str]] = defaultdict(Counter)
    successors: dict[str, Counter[str]] = defaultdict(Counter)
    for edge in graph.edges:
        successors[edge.source][labels[edge.target]] += 1
        predecessors[edge.target][labels[edge.source]] += 1
    return {node.id: (predecessors[node.id], successors[node.id]) for node in graph.nodes}


def _context_similarity(a: _Context, b: _Context) -> float:
    return (_multiset_jaccard(a[0], b[0]) + _multiset_jaccard(a[1], b[1])) / 2


def _multiset_jaccard(a: Counter[str], b: Counter[str]) -> float:
    union = sum((a | b).values())
    return sum((a & b).values()) / union if union else 1.0
