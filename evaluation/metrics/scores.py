"""Per-sample scores of one prediction against its ground truth (spec §20.2–20.8, §23).

Every score is computed from the §20.1 node matching (``matching.py``, matching v1).
``SCORES_VERSION`` pins the definitions below; changing one is a versioned decision —
bump it and record why in CLAUDE.md.

Definitions, scores v1:

- **Validity** (§20.2), from the Stage C result: first-attempt validity (the first model
  output was a valid graph), the stricter bare-JSON variant (and that output was nothing
  but the JSON object), and post-repair validity (a graph came out of Stage C at all).
- **Failed predictions** (no graph) score as an empty prediction: P/R/F1 0 (recall 0,
  precision 0 by the zero-division convention, since ground truth is never empty), graph
  similarity 0, diagram type wrong. Label, edge-label and grouping scores are undefined
  (nothing matched) and the error taxonomy is not computed — failures are counted
  separately, not as omissions.
- **Node / edge P/R/F1** (§20.3–20.4): straight from the matching; edges loose (direction)
  and strict (direction + relation).
- **Graph similarity** (§20.5), the primary graph metric: 1 − cost / (|V_p| + |V_g| + |E_p|
  + |E_g|), where cost is the edit cost of turning the prediction into the ground truth
  *under the §20.1 assignment*: 1 per unmatched node (deletion or insertion), 1 − pair
  similarity per matched node (relabel/retype; a perfect pair costs 0), 1 per unmatched
  edge (loose variant), 1 per matched edge whose relation differs. It is 1 for graphs
  identical up to ids and 0 when nothing matches. It is the edit distance of one specific
  alignment, i.e. an upper bound on the minimum graph edit distance under these costs —
  chosen because exact GED is intractable at 40 nodes and because it agrees by
  construction with the node/edge metrics. Edge text and grouping are scored separately.
- **Label accuracy** (§20.6), on matched nodes only: exact match after Stage D text
  normalization (NFC + whitespace), case-sensitive and case-insensitive; normalized
  Levenshtein similarity; CER = character edits / ground-truth characters; WER = word
  edits / ground-truth words (both pooled over labels, may exceed 1).
- **Edge text** (§23 type 10), on loose-matched edges: an edge's text is its label, else
  its condition, normalized and casefolded. Accuracy is over matched edges whose
  ground truth has text; lost / wrong / hallucinated are counted.
- **Grouping** (§23 type 11), on matched nodes: the prediction's group (mapped through the
  assignment) must equal the ground truth's group. Flattened, wrongly nested, and wrong
  group are counted.
- **Diagram type** (§20.8): exact enum equality.
"""

from __future__ import annotations

from pydantic import BaseModel
from rapidfuzz.distance import Levenshtein

from app.pipeline.extraction import ExtractionResult, ExtractionStatus
from app.pipeline.normalize import normalize_text
from app.schemas import DiagramGraph, Edge
from evaluation.metrics.errors import ErrorCounts, classify_errors
from evaluation.metrics.matching import PRF, MatchResult, match_graphs, prf

SCORES_VERSION = "1"


class Validity(BaseModel):
    status: ExtractionStatus
    first_attempt: bool
    first_attempt_bare_json: bool
    post_repair: bool
    attempts: int
    repairs: int


def validity(extraction: ExtractionResult) -> Validity:
    first = extraction.attempts[0]
    return Validity(
        status=extraction.status,
        first_attempt=extraction.status == "valid_first_attempt",
        first_attempt_bare_json=first.valid and first.json_method == "direct",
        post_repair=extraction.status != "failed",
        attempts=len(extraction.attempts),
        repairs=len(extraction.repairs),
    )


class LabelScores(BaseModel):
    matched: int
    exact: int
    exact_casefold: int
    similarity_sum: float
    char_edits: int
    chars: int
    word_edits: int
    words: int


class EdgeTextScores(BaseModel):
    matched_with_text: int  # matched edges whose ground truth has text
    correct: int
    lost: int  # ground truth has text, prediction has none
    wrong: int  # both have text, and it differs
    hallucinated: int  # prediction has text, ground truth has none


class GroupingScores(BaseModel):
    matched: int
    correct: int
    flattened: int  # grouped in the ground truth, not in the prediction
    wrongly_nested: int  # grouped in the prediction, not in the ground truth
    wrong_group: int  # grouped in both, but in different groups


class SampleScores(BaseModel):
    scores_version: str = SCORES_VERSION
    has_graph: bool
    nodes: PRF
    edges: PRF
    edges_strict: PRF
    graph_similarity: float
    diagram_type_correct: bool
    labels: LabelScores | None  # None when no graph was predicted
    edge_text: EdgeTextScores | None
    grouping: GroupingScores | None
    errors: ErrorCounts | None


def score_sample(predicted: DiagramGraph | None, ground_truth: DiagramGraph) -> SampleScores:
    if predicted is None:
        nodes = prf(0, 0, len(ground_truth.nodes))
        edges = prf(0, 0, len(ground_truth.edges))
        return SampleScores(
            has_graph=False,
            nodes=nodes,
            edges=edges,
            edges_strict=edges,
            graph_similarity=0.0,
            diagram_type_correct=False,
            labels=None,
            edge_text=None,
            grouping=None,
            errors=None,
        )
    match = match_graphs(predicted, ground_truth)
    edge_text = edge_text_scores(predicted, ground_truth, match)
    grouping = grouping_scores(predicted, ground_truth, match)
    return SampleScores(
        has_graph=True,
        nodes=match.nodes,
        edges=match.edges,
        edges_strict=match.edges_strict,
        graph_similarity=graph_similarity(predicted, ground_truth, match),
        diagram_type_correct=predicted.diagram_type == ground_truth.diagram_type,
        labels=label_scores(predicted, ground_truth, match),
        edge_text=edge_text,
        grouping=grouping,
        errors=classify_errors(
            predicted,
            ground_truth,
            match,
            edge_text_errors=edge_text.lost + edge_text.wrong + edge_text.hallucinated,
            grouping_errors=grouping.matched - grouping.correct,
        ),
    )


def graph_similarity(
    predicted: DiagramGraph, ground_truth: DiagramGraph, match: MatchResult
) -> float:
    size = (
        len(predicted.nodes)
        + len(ground_truth.nodes)
        + len(predicted.edges)
        + len(ground_truth.edges)
    )
    if size == 0:
        return 1.0
    cost = (
        len(match.unmatched_predicted)
        + len(match.unmatched_ground_truth)
        + sum(1.0 - pair.similarity for pair in match.node_pairs)
        + match.edges.fp
        + match.edges.fn
        + sum(
            predicted.edges[p].relation != ground_truth.edges[g].relation
            for p, g in match.edge_pairs
        )
    )
    return max(0.0, 1.0 - cost / size)


def label_scores(
    predicted: DiagramGraph, ground_truth: DiagramGraph, match: MatchResult
) -> LabelScores:
    pred_labels = {n.id: normalize_text(n.label) for n in predicted.nodes}
    gt_labels = {n.id: normalize_text(n.label) for n in ground_truth.nodes}
    scores = LabelScores(
        matched=0,
        exact=0,
        exact_casefold=0,
        similarity_sum=0.0,
        char_edits=0,
        chars=0,
        word_edits=0,
        words=0,
    )
    for pair in match.node_pairs:
        p, g = pred_labels[pair.predicted], gt_labels[pair.ground_truth]
        scores.matched += 1
        scores.exact += p == g
        scores.exact_casefold += p.casefold() == g.casefold()
        scores.similarity_sum += Levenshtein.normalized_similarity(p, g)
        scores.char_edits += Levenshtein.distance(p, g)
        scores.chars += len(g)
        scores.word_edits += Levenshtein.distance(p.split(), g.split())
        scores.words += len(g.split())
    return scores


def edge_text(edge: Edge) -> str | None:
    for text in (edge.label, edge.condition):
        if text and text.strip():
            return normalize_text(text).casefold()
    return None


def edge_text_scores(
    predicted: DiagramGraph, ground_truth: DiagramGraph, match: MatchResult
) -> EdgeTextScores:
    scores = EdgeTextScores(matched_with_text=0, correct=0, lost=0, wrong=0, hallucinated=0)
    for p, g in match.edge_pairs:
        pred_text, gt_text = edge_text(predicted.edges[p]), edge_text(ground_truth.edges[g])
        if gt_text is None:
            scores.hallucinated += pred_text is not None
            continue
        scores.matched_with_text += 1
        if pred_text is None:
            scores.lost += 1
        elif pred_text == gt_text:
            scores.correct += 1
        else:
            scores.wrong += 1
    return scores


def grouping_scores(
    predicted: DiagramGraph, ground_truth: DiagramGraph, match: MatchResult
) -> GroupingScores:
    pred_group = {n.id: n.group_id for n in predicted.nodes}
    gt_group = {n.id: n.group_id for n in ground_truth.nodes}
    mapping = match.assignment
    scores = GroupingScores(matched=0, correct=0, flattened=0, wrongly_nested=0, wrong_group=0)
    for pair in match.node_pairs:
        scores.matched += 1
        expected = gt_group[pair.ground_truth]
        predicted_group = pred_group[pair.predicted]
        actual = None if predicted_group is None else mapping.get(predicted_group, "<unmatched>")
        if actual == expected:
            scores.correct += 1
        elif actual is None:
            scores.flattened += 1
        elif expected is None:
            scores.wrongly_nested += 1
        else:
            scores.wrong_group += 1
    return scores
