from typing import Any

import numpy as np
import pytest

from app.schemas import DiagramGraph
from evaluation.metrics.matching import (
    MATCHING_VERSION,
    THRESHOLD,
    assign,
    match_graphs,
    matching_config,
    prf,
)


def graph(nodes: list[tuple], edges: list[tuple] = ()) -> DiagramGraph:
    """nodes: (id, label[, type]); edges: (source, target[, relation])."""
    return DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": "neural_network",
            "nodes": [
                {"id": n[0], "label": n[1], "type": n[2] if len(n) > 2 else "module"} for n in nodes
            ],
            "edges": [
                {"source": e[0], "target": e[1], "relation": e[2] if len(e) > 2 else "flows_to"}
                for e in edges
            ],
        }
    )


SPEC_NODES = [
    ("n1", "Input Image", "input"),
    ("n2", "CNN Encoder"),
    ("n3", "Transformer Encoder"),
    ("n4", "Feature Fusion", "fusion"),
    ("n5", "Classifier", "output"),
]
SPEC_EDGES = [("n1", "n2"), ("n1", "n3"), ("n2", "n4"), ("n3", "n4"), ("n4", "n5")]


def perfect(result: Any) -> bool:
    return all(m.f1 == 1.0 for m in (result.nodes, result.edges, result.edges_strict))


# --- whole-graph behaviour ------------------------------------------------------------


def test_identical_graphs_match_perfectly() -> None:
    gt = graph(SPEC_NODES, SPEC_EDGES)

    result = match_graphs(gt, gt)

    assert perfect(result)
    assert result.assignment == {f"n{i}": f"n{i}" for i in range(1, 6)}
    assert result.matching_version == MATCHING_VERSION


def test_ids_do_not_matter() -> None:
    rename = {"n1": "a", "n2": "b", "n3": "c", "n4": "d", "n5": "e"}
    pred = graph(
        [(rename[n[0]], *n[1:]) for n in reversed(SPEC_NODES)],
        [(rename[s], rename[t]) for s, t in SPEC_EDGES],
    )

    result = match_graphs(pred, graph(SPEC_NODES, SPEC_EDGES))

    assert perfect(result)
    assert result.assignment == {v: k for k, v in rename.items()}


def test_labels_match_case_and_whitespace_insensitively() -> None:
    result = match_graphs(graph([("p", "cnn  encoder")]), graph([("g", "CNN Encoder")]))

    assert result.node_pairs[0].label_similarity == 1.0


# --- node matching --------------------------------------------------------------------


def test_label_corruption_at_the_threshold_still_matches() -> None:
    result = match_graphs(graph([("p", "Multi Head Attn")]), graph([("g", "Multi-Head Attention")]))

    pair = result.node_pairs[0]
    assert pair.label_similarity == pytest.approx(0.70)
    assert pair.similarity == pytest.approx(0.75)  # + type bonus


def test_dissimilar_labels_do_not_match() -> None:
    result = match_graphs(graph([("p", "Fusion")]), graph([("g", "Feature Fusion")]))

    assert result.node_pairs == []
    assert result.unmatched_predicted == ["p"] and result.unmatched_ground_truth == ["g"]
    assert (result.nodes.tp, result.nodes.fp, result.nodes.fn) == (0, 1, 1)


def test_type_mismatch_can_push_a_pair_below_the_threshold() -> None:
    # "Encoder" vs "Decoder" has label similarity 0.714: a known weakness of edit distance
    # on short labels. Same type: matched; different type: 0.664 < 0.70, not matched.
    same = match_graphs(graph([("p", "Decoder")]), graph([("g", "Encoder")]))
    different = match_graphs(graph([("p", "Decoder", "output")]), graph([("g", "Encoder")]))

    assert len(same.node_pairs) == 1
    assert different.node_pairs == []


def test_type_breaks_ties_between_identical_labels() -> None:
    pred = graph([("p1", "Pool", "module"), ("p2", "Pool", "operation")])

    result = match_graphs(pred, graph([("g", "Pool", "operation")]))

    assert result.assignment == {"p2": "g"}
    assert result.unmatched_predicted == ["p1"]


def test_matching_is_one_to_one() -> None:
    result = match_graphs(graph([("a", "ReLU"), ("b", "ReLU")]), graph([("g", "ReLU")]))

    assert (result.nodes.tp, result.nodes.fp, result.nodes.fn) == (1, 1, 0)


def test_hallucinated_and_omitted_nodes_count_against_precision_and_recall() -> None:
    pred = graph([("n1", "Input Image", "input"), ("x", "Dropout"), ("n5", "Classifier", "output")])

    result = match_graphs(pred, graph(SPEC_NODES))

    assert result.unmatched_predicted == ["x"]
    assert result.unmatched_ground_truth == ["n2", "n3", "n4"]
    assert result.nodes.precision == pytest.approx(2 / 3)
    assert result.nodes.recall == pytest.approx(2 / 5)


def test_repeated_labels_are_assigned_by_their_neighbourhood() -> None:
    # in -> conv -> relu -> conv -> out, with the predicted convs listed in the other order.
    gt = graph(
        [("in", "Input"), ("c1", "Conv 3x3"), ("r", "ReLU"), ("c2", "Conv 3x3"), ("out", "Out")],
        [("in", "c1"), ("c1", "r"), ("r", "c2"), ("c2", "out")],
    )
    pred = graph(
        [("i", "Input"), ("b", "Conv 3x3"), ("x", "ReLU"), ("a", "Conv 3x3"), ("o", "Out")],
        [("i", "a"), ("a", "x"), ("x", "b"), ("b", "o")],
    )

    result = match_graphs(pred, gt)

    assert result.assignment["a"] == "c1" and result.assignment["b"] == "c2"
    assert result.edges.f1 == 1.0


# --- edge scoring ---------------------------------------------------------------------


def test_reversed_edge_is_a_false_positive_and_a_false_negative() -> None:
    nodes = [("a", "Alpha"), ("b", "Beta")]

    result = match_graphs(graph(nodes, [("b", "a")]), graph(nodes, [("a", "b")]))

    assert (result.edges.tp, result.edges.fp, result.edges.fn) == (0, 1, 1)
    assert [(e.source, e.target) for e in result.edge_false_positives] == [("b", "a")]
    assert [(e.source, e.target) for e in result.edge_false_negatives] == [("a", "b")]


def test_relation_only_matters_for_the_strict_variant() -> None:
    nodes = [("a", "Alpha"), ("b", "Beta")]

    result = match_graphs(
        graph(nodes, [("a", "b", "depends_on")]), graph(nodes, [("a", "b", "flows_to")])
    )

    assert result.edges.f1 == 1.0
    assert (result.edges_strict.tp, result.edges_strict.fp, result.edges_strict.fn) == (0, 1, 1)


def test_edges_touching_unmatched_nodes_are_false_positives() -> None:
    pred = graph([("a", "Alpha"), ("z", "Dropout")], [("a", "z")])

    result = match_graphs(pred, graph([("a", "Alpha"), ("b", "Beta")], [("a", "b")]))

    assert (result.edges.tp, result.edges.fp, result.edges.fn) == (0, 1, 1)


def test_each_ground_truth_edge_is_claimed_once() -> None:
    nodes = [("a", "Alpha"), ("b", "Beta")]
    pred = graph(nodes, [("a", "b", "flows_to"), ("a", "b", "depends_on")])

    result = match_graphs(pred, graph(nodes, [("a", "b")]))

    assert (result.edges.tp, result.edges.fp, result.edges.fn) == (1, 1, 0)


def test_parallel_ground_truth_edges_are_each_counted() -> None:
    nodes = [("a", "Alpha"), ("b", "Beta")]
    gt = graph(nodes, [("a", "b", "flows_to"), ("a", "b", "depends_on")])

    result = match_graphs(graph(nodes, [("a", "b")]), gt)

    assert (result.edges.tp, result.edges.fp, result.edges.fn) == (1, 0, 1)


def test_graphs_without_edges_score_edges_perfectly() -> None:
    result = match_graphs(graph([("a", "Alpha")]), graph([("a", "Alpha")]))

    assert result.edges == prf(0, 0, 0)
    assert result.edges.f1 == 1.0


# --- building blocks ------------------------------------------------------------------


def test_hungarian_assignment_beats_greedy() -> None:
    # Greedy takes (0, 0) = 0.9 and leaves row 1 with nothing eligible: one match.
    # The optimum pairs (0, 1) and (1, 0): two matches.
    similarity = np.array([[0.90, 0.85], [0.88, 0.10]])

    assert sorted(assign(similarity, similarity)) == [(0, 1), (1, 0)]


def test_assignment_never_returns_ineligible_pairs() -> None:
    similarity = np.array([[0.5, 0.2], [0.1, 0.95]])

    assert assign(similarity, similarity) == [(1, 1)]


def test_assignment_handles_empty_and_rectangular_input() -> None:
    assert assign(np.zeros((0, 3)), np.zeros((0, 3))) == []
    assert assign(np.array([[0.8, 0.9, 0.1]]), np.array([[0.8, 0.9, 0.1]])) == [(0, 1)]


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ((2, 1, 1), (2 / 3, 2 / 3, 2 / 3)),
        ((0, 0, 0), (1.0, 1.0, 1.0)),
        ((0, 0, 3), (0.0, 0.0, 0.0)),
        ((0, 2, 0), (0.0, 0.0, 0.0)),
        ((0, 1, 1), (0.0, 0.0, 0.0)),
    ],
    ids=["normal", "nothing-at-all", "predicted-nothing", "nothing-to-find", "all-wrong"],
)
def test_prf_conventions(counts: tuple[int, int, int], expected: tuple[float, ...]) -> None:
    result = prf(*counts)

    assert (result.precision, result.recall, result.f1) == pytest.approx(expected)


def test_config_documents_the_definition() -> None:
    config = matching_config()

    assert config["matching_version"] == MATCHING_VERSION
    assert config["threshold"] == THRESHOLD == 0.70
    assert config["rapidfuzz_version"] and config["scipy_version"]
