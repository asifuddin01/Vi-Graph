import json
import random
from pathlib import Path

import networkx as nx
import pytest
from PIL import Image
from rapidfuzz.distance import Levenshtein

from app.pipeline.extraction import extract_graph
from app.pipeline.normalize import normalize_text
from app.schemas import DiagramGraph
from app.vlm.mock import MockVLM
from evaluation.metrics.matching import TYPE_BONUS, TYPE_PENALTY, match_graphs, matching_label
from evaluation.metrics.scores import edge_text, score_sample, validity
from evaluation.tests.helpers import graph

EXAMPLES = Path(__file__).resolve().parents[2] / "examples" / "outputs"


CHAIN = graph(
    [("a", "Input", "input"), ("b", "Encoder"), ("c", "Decoder"), ("d", "Output", "output")],
    [("a", "b"), ("b", "c"), ("c", "d")],
)


# --- whole-sample behaviour -----------------------------------------------------------


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.stem)
def test_ground_truth_scores_perfectly_against_itself(path: Path) -> None:
    gt = DiagramGraph.model_validate_json(path.read_text())

    scores = score_sample(gt, gt)

    assert scores.nodes.f1 == scores.edges.f1 == scores.edges_strict.f1 == 1.0
    assert scores.graph_similarity == 1.0
    assert scores.diagram_type_correct
    assert scores.labels.exact == scores.labels.matched == len(gt.nodes)
    assert scores.labels.char_edits == 0
    assert scores.edge_text.correct == scores.edge_text.matched_with_text
    assert scores.grouping.correct == scores.grouping.matched
    assert not any(scores.errors.model_dump().values())


def test_ids_and_order_do_not_matter() -> None:
    shuffled = graph(
        [
            ("x4", "Output", "output"),
            ("x2", "Encoder"),
            ("x1", "Input", "input"),
            ("x3", "Decoder"),
        ],
        [("x3", "x4"), ("x1", "x2"), ("x2", "x3")],
    )

    scores = score_sample(shuffled, CHAIN)

    assert scores.graph_similarity == 1.0
    assert scores.edges.f1 == 1.0


def test_failed_prediction_scores_zero_and_skips_the_taxonomy() -> None:
    scores = score_sample(None, CHAIN)

    assert not scores.has_graph
    assert (scores.nodes.tp, scores.nodes.fn, scores.nodes.f1) == (0, 4, 0.0)
    assert (scores.edges.fn, scores.edges.precision, scores.edges.recall) == (3, 0.0, 0.0)
    assert scores.graph_similarity == 0.0
    assert not scores.diagram_type_correct
    assert scores.labels is None and scores.errors is None


def test_diagram_type_accuracy() -> None:
    other = CHAIN.model_copy(update={"diagram_type": "neural_network"})

    assert not score_sample(other, CHAIN).diagram_type_correct


# --- graph similarity -----------------------------------------------------------------


def test_graph_similarity_counts_one_per_missing_node_and_edge() -> None:
    # Missing "Output" and c->d: cost 2, size 3 + 4 + 2 + 3 = 12.
    pred = graph(
        [("a", "Input", "input"), ("b", "Encoder"), ("c", "Decoder")], [("a", "b"), ("b", "c")]
    )

    assert score_sample(pred, CHAIN).graph_similarity == pytest.approx(1 - 2 / 12)


def test_graph_similarity_charges_relabel_retype_and_relation_changes() -> None:
    pred = graph(
        [
            ("a", "Input", "input"),
            ("b", "Encodr"),
            ("c", "Decoder", "operation"),
            ("d", "Output", "output"),
        ],
        [("a", "b"), ("b", "c", "depends_on"), ("c", "d")],
    )
    relabel = 1 - min(1.0, Levenshtein.normalized_similarity("encodr", "encoder") + TYPE_BONUS)
    retype = TYPE_PENALTY  # label identical, type differs: similarity 0.95

    scores = score_sample(pred, CHAIN)

    assert scores.edges.f1 == 1.0 and scores.edges_strict.tp == 2
    assert scores.graph_similarity == pytest.approx(1 - (relabel + retype + 1) / 14)


def test_graph_similarity_is_zero_when_nothing_matches() -> None:
    pred = graph([("p", "Completely unrelated"), ("q", "Something else")], [("p", "q")])

    assert score_sample(pred, CHAIN).graph_similarity == 0.0


def _exact_ged(predicted: DiagramGraph, ground_truth: DiagramGraph) -> float:
    def as_nx(g: DiagramGraph) -> nx.DiGraph:
        out = nx.DiGraph()
        for n in g.nodes:
            out.add_node(n.id, label=matching_label(n.label), type=n.type)
        for e in g.edges:
            out.add_edge(e.source, e.target, relation=e.relation)
        return out

    def node_subst(a: dict, b: dict) -> float:
        sim = Levenshtein.normalized_similarity(a["label"], b["label"])
        sim += TYPE_BONUS if a["type"] == b["type"] else -TYPE_PENALTY
        return 1 - min(1.0, max(0.0, sim))

    return nx.graph_edit_distance(
        as_nx(predicted),
        as_nx(ground_truth),
        node_subst_cost=node_subst,
        edge_subst_cost=lambda a, b: float(a["relation"] != b["relation"]),
        timeout=10,
    )


@pytest.mark.parametrize("seed", range(6))
def test_graph_similarity_cost_is_never_below_the_exact_edit_distance(seed: int) -> None:
    rng = random.Random(seed)
    words = ["Input", "Encoder", "Decoder", "Output", "Pool", "Norm", "Attention"]
    gt_nodes = [(f"g{i}", words[i]) for i in range(5)]
    gt = graph(gt_nodes, [(f"g{i}", f"g{i + 1}") for i in range(4)])
    pred_nodes = [(f"p{i}", rng.choice(words)) for i in range(rng.randint(3, 5))]
    pairs = [(a[0], b[0]) for a in pred_nodes for b in pred_nodes if a != b]
    pred = graph(pred_nodes, rng.sample(pairs, rng.randint(1, 4)))

    scores = score_sample(pred, gt)
    size = len(pred.nodes) + len(gt.nodes) + len(pred.edges) + len(gt.edges)
    cost = (1 - scores.graph_similarity) * size

    assert cost >= _exact_ged(pred, gt) - 1e-9


# --- labels, edge text, grouping ------------------------------------------------------


def test_label_scores_on_matched_nodes_only() -> None:
    pred = graph(
        [("a", "input", "input"), ("b", "Encodr"), ("c", "Decoder"), ("z", "Hallucinated")],
        [("a", "b"), ("b", "c")],
    )

    labels = score_sample(pred, CHAIN).labels

    assert labels.matched == 3  # Output is missing; the hallucination is unmatched
    assert labels.exact == 1  # Decoder
    assert labels.exact_casefold == 2  # + input/Input
    assert labels.char_edits == 1 + 1  # I→i, Encodr → Encoder
    assert labels.chars == len("Input") + len("Encoder") + len("Decoder")
    assert labels.word_edits == 2 and labels.words == 3


def test_label_comparison_uses_stage_d_text_normalization() -> None:
    pred = graph(
        [("a", "  Input  ", "input"), ("b", "Encoder"), ("c", "Decoder"), ("d", "Output", "output")]
    )
    assert normalize_text("  Input  ") == "Input"

    assert score_sample(pred, CHAIN).labels.exact == 4


def test_edge_text_uses_label_then_condition() -> None:
    labeled = graph([("a", "A"), ("b", "B")], [("a", "b", "flows_to", "  Yes ")])
    conditioned = DiagramGraph.model_validate(
        labeled.model_dump()
        | {"edges": [{"source": "a", "target": "b", "relation": "flows_to", "condition": "x > 0"}]}
    )

    assert edge_text(labeled.edges[0]) == "yes"
    assert edge_text(conditioned.edges[0]) == "x > 0"


def test_edge_text_scores_count_lost_wrong_and_hallucinated() -> None:
    nodes = [("d", "Ready?", "decision"), ("y", "Ship"), ("n", "Fix"), ("e", "End")]
    gt = graph(
        nodes, [("d", "y", "flows_to", "Yes"), ("d", "n", "flows_to", "No"), ("y", "e"), ("n", "e")]
    )
    pred = graph(
        nodes,
        [("d", "y", "flows_to", "yes"), ("d", "n"), ("y", "e", "flows_to", "done"), ("n", "e")],
    )
    swapped = graph(
        nodes, [("d", "y", "flows_to", "No"), ("d", "n", "flows_to", "Yes"), ("y", "e"), ("n", "e")]
    )

    text = score_sample(pred, gt).edge_text

    assert (text.matched_with_text, text.correct, text.lost, text.wrong, text.hallucinated) == (
        2,
        1,
        1,
        0,
        1,
    )
    assert score_sample(pred, gt).errors.edge_label_loss == 2
    assert score_sample(swapped, gt).edge_text.wrong == 2


def test_grouping_scores() -> None:
    gt = graph(
        [
            ("g", "Backbone", "group"),
            ("h", "Head", "group"),
            ("a", "Conv", "module", "g"),
            ("b", "Pool", "module", "g"),
            ("c", "Linear", "module", "h"),
            ("d", "Softmax"),
        ],
        [("a", "b"), ("b", "c"), ("c", "d")],
    )
    pred = graph(
        [
            ("G", "Backbone", "group"),
            ("H", "Head", "group"),
            ("A", "Conv", "module", "G"),
            ("B", "Pool"),
            ("C", "Linear", "module", "G"),
            ("D", "Softmax", "module", "H"),
        ],
        [("A", "B"), ("B", "C"), ("C", "D")],
    )

    grouping = score_sample(pred, gt).grouping

    assert grouping.matched == 6
    assert grouping.correct == 3  # the two groups themselves + Conv
    assert (grouping.flattened, grouping.wrong_group, grouping.wrongly_nested) == (1, 1, 1)
    assert score_sample(pred, gt).errors.grouping_failure == 3


# --- error taxonomy -------------------------------------------------------------------


def test_reversed_wrong_missing_and_spurious_edges() -> None:
    gt = graph(
        [("a", "Alpha"), ("b", "Bravo"), ("c", "Charlie"), ("d", "Delta")],
        [("a", "b"), ("b", "c"), ("c", "d"), ("a", "d")],
    )
    pred = graph(
        [("a", "Alpha"), ("b", "Bravo"), ("c", "Charlie"), ("d", "Delta"), ("x", "Xylophone")],
        # b->a reversed; a->c instead of a->d (wrong target); c->d missing; d->x spurious
        [("b", "a"), ("b", "c"), ("a", "c"), ("d", "x")],
    )

    errors = score_sample(pred, gt).errors

    assert errors.reversed_edge == 1
    assert errors.wrong_edge == 1
    assert errors.missing_edge == 1
    assert errors.spurious_edge == 1
    assert errors.node_hallucination == 1 and errors.node_omission == 0


def test_wrong_source_counts_as_wrong_edge() -> None:
    pred = graph(
        [("a", "Input", "input"), ("b", "Encoder"), ("c", "Decoder"), ("d", "Output", "output")],
        [("a", "b"), ("a", "c"), ("c", "d")],  # expected b->c, got a->c
    )

    errors = score_sample(pred, CHAIN).errors

    assert (errors.wrong_edge, errors.missing_edge, errors.spurious_edge) == (1, 0, 0)


def test_branch_and_merge_confusion() -> None:
    # Fork f → {x, y} merging at m.
    nodes = [("f", "Fork"), ("x", "Left branch"), ("y", "Right branch"), ("m", "Merge", "fusion")]
    gt = graph(nodes, [("f", "x"), ("f", "y"), ("x", "m"), ("y", "m")])
    wrong_branch = graph(nodes, [("f", "x"), ("x", "y"), ("x", "m"), ("y", "m")])
    missed_merge = graph(nodes, [("f", "x"), ("f", "y"), ("x", "m")])

    assert score_sample(wrong_branch, gt).errors.branch_confusion == 1
    assert score_sample(wrong_branch, gt).errors.merge_confusion == 0
    assert score_sample(missed_merge, gt).errors.merge_confusion == 1
    assert score_sample(missed_merge, gt).errors.branch_confusion == 0


def test_omission_hallucination_and_label_corruption() -> None:
    pred = graph(
        [("a", "Input", "input"), ("b", "Encodr"), ("c", "Decoder"), ("z", "Zebra crossing")],
        [("a", "b"), ("b", "c")],
    )

    errors = score_sample(pred, CHAIN).errors

    assert errors.node_omission == 1  # Output
    assert errors.node_hallucination == 1  # Zebra crossing
    assert errors.label_corruption == 1  # Encodr
    assert errors.missing_edge == 1  # c->d


def test_perturbed_synthetic_graph() -> None:
    gt = DiagramGraph.model_validate_json(
        (EXAMPLES / "L3-system-architecture-layered-lr-corporate.json").read_text()
    )
    victim = next(n for n in gt.nodes if n.type != "group")
    kept_edges = [e for e in gt.edges if victim.id not in (e.source, e.target)]
    pred = DiagramGraph.model_validate(
        gt.model_dump()
        | {
            "nodes": [n.model_dump() for n in gt.nodes if n.id != victim.id],
            "edges": [e.model_dump() for e in kept_edges],
        }
    )

    scores = score_sample(pred, gt)

    assert scores.nodes.fn == 1 and scores.nodes.fp == 0
    assert scores.edges.fn == len(gt.edges) - len(kept_edges) and scores.edges.fp == 0
    assert scores.errors.node_omission == 1
    assert scores.errors.missing_edge == scores.edges.fn
    assert 0 < scores.graph_similarity < 1


# --- validity -------------------------------------------------------------------------


GT_JSON = CHAIN.model_dump_json()


@pytest.mark.parametrize(
    ("responses", "expected"),
    [
        ([GT_JSON], ("valid_first_attempt", True, True, True)),
        ([f"```json\n{GT_JSON}\n```"], ("valid_first_attempt", True, False, True)),
        (["no json here", GT_JSON], ("valid_after_retry", False, False, True)),
        (["nope", "still nope"], ("failed", False, False, False)),
    ],
)
def test_validity(responses: list[str], expected: tuple) -> None:
    extraction = extract_graph(MockVLM(responses), [Image.new("RGB", (32, 32))])

    result = validity(extraction)

    assert (
        result.status,
        result.first_attempt,
        result.first_attempt_bare_json,
        result.post_repair,
    ) == expected


def test_match_exposes_claimed_edge_pairs() -> None:
    pred = graph(
        [("x", "Decoder"), ("y", "Output", "output"), ("z", "Input", "input"), ("w", "Encoder")],
        [("x", "y"), ("z", "x"), ("z", "w")],
    )

    match = match_graphs(pred, CHAIN)

    assert match.edge_pairs == [(0, 2), (2, 0)]
    assert json.loads(match.model_dump_json())["edge_pairs"] == [[0, 2], [2, 0]]
