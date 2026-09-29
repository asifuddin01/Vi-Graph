import json
from pathlib import Path
from typing import Any

from app.pipeline.normalize import NormalizationCode, normalize_graph, normalize_text
from app.schemas import DiagramGraph

FIXTURES = Path(__file__).parent / "fixtures"


def build(nodes: list[dict], edges: list[dict] | None = None) -> DiagramGraph:
    return DiagramGraph.model_validate(
        {"schema_version": "2.0", "diagram_type": "flowchart", "nodes": nodes, "edges": edges or []}
    )


def node(node_id: str, label: str | None = None, **extra: Any) -> dict:
    return {"id": node_id, "label": label or node_id.upper(), "type": "module", **extra}


def edge(source: str, target: str, relation: str = "flows_to", **extra: Any) -> dict:
    return {"source": source, "target": target, "relation": relation, **extra}


def codes(result: Any) -> list[NormalizationCode]:
    return [change.code for change in result.changes]


def test_spec_example_is_already_normal() -> None:
    graph = DiagramGraph.model_validate_json((FIXTURES / "graph_v2_example.json").read_text())

    result = normalize_graph(graph)

    assert result.changes == []
    assert result.graph == graph
    assert result.id_map == {f"n{i}": f"n{i}" for i in range(1, 6)}


def test_input_graph_is_not_modified() -> None:
    graph = build([node("a", "  A "), node("b")], [edge("a", "b"), edge("a", "b")])
    snapshot = graph.model_copy(deep=True)

    normalize_graph(graph)

    assert graph == snapshot


def test_normalize_text() -> None:
    assert normalize_text("  Multi-Head\n  Attention\t") == "Multi-Head Attention"
    assert normalize_text("Non breaking") == "Non breaking"
    assert normalize_text("Café") == "Café"


def test_node_labels_are_normalized_and_recorded() -> None:
    result = normalize_graph(build([node("n1", "  CNN\n Encoder ")]))

    assert result.graph.nodes[0].label == "CNN Encoder"
    assert codes(result) == [NormalizationCode.NORMALIZED_TEXT]
    assert result.changes[0].message == "node 'n1' label '  CNN\\n Encoder ' -> 'CNN Encoder'"


def test_edge_text_is_normalized_and_blank_becomes_null() -> None:
    result = normalize_graph(
        build(
            [node("n1"), node("n2"), node("n3")],
            [edge("n1", "n2", label="  Yes ", condition=""), edge("n1", "n3", label="   ")],
        )
    )

    assert [(e.label, e.condition) for e in result.graph.edges] == [("Yes", None), (None, None)]
    assert codes(result) == [
        NormalizationCode.NORMALIZED_TEXT,
        NormalizationCode.EMPTY_TEXT_TO_NULL,
        NormalizationCode.EMPTY_TEXT_TO_NULL,
    ]


def test_duplicate_edges_are_removed_after_text_normalization() -> None:
    result = normalize_graph(
        build(
            [node("n1"), node("n2")],
            [edge("n1", "n2", label="Yes"), edge("n1", "n2", label=" Yes"), edge("n1", "n2")],
        )
    )

    assert [(e.source, e.target, e.label) for e in result.graph.edges] == [
        ("n1", "n2", "Yes"),
        ("n1", "n2", None),
    ]
    assert codes(result)[-1] == NormalizationCode.REMOVED_DUPLICATE_EDGE


def test_distinct_edges_between_the_same_nodes_are_kept() -> None:
    edges = [edge("n1", "n2"), edge("n2", "n1"), edge("n1", "n2", "depends_on"), edge("n1", "n1")]

    result = normalize_graph(build([node("n1"), node("n2")], edges))

    assert len(result.graph.edges) == 4
    assert result.changes == []


def test_ids_are_renumbered_with_edges_and_groups_following() -> None:
    graph = build(
        [
            node("encoder_block", type="group"),
            node("input"),
            node("conv", group_id="encoder_block"),
        ],
        [edge("input", "conv"), edge("conv", "encoder_block", "depends_on")],
    )

    result = normalize_graph(graph)

    assert result.id_map == {"encoder_block": "n1", "input": "n2", "conv": "n3"}
    assert [n.id for n in result.graph.nodes] == ["n1", "n2", "n3"]
    assert result.graph.nodes[2].group_id == "n1"
    assert [(e.source, e.target) for e in result.graph.edges] == [("n2", "n3"), ("n3", "n1")]
    assert codes(result) == [NormalizationCode.RENUMBERED_IDS]
    assert result.changes[0].message == "renumbered 3 of 3 node ids to n1..n3 (see id_map)"


def test_out_of_order_ids_are_renumbered() -> None:
    result = normalize_graph(build([node("n2"), node("n1")], [edge("n2", "n1")]))

    assert result.id_map == {"n2": "n1", "n1": "n2"}
    assert [(e.source, e.target) for e in result.graph.edges] == [("n1", "n2")]


def test_topology_is_preserved_exactly_under_the_id_map() -> None:
    edges = [edge("a", "b"), edge("b", "c"), edge("a", "c", "branches_to", label="skip")]
    graph = build([node("a"), node("b"), node("c")], edges)

    result = normalize_graph(graph)

    mapped = {
        (result.id_map[e.source], result.id_map[e.target], e.relation, e.label) for e in graph.edges
    }
    assert {(e.source, e.target, e.relation, e.label) for e in result.graph.edges} == mapped


def test_duplicate_labels_are_flagged_not_merged() -> None:
    result = normalize_graph(
        build([node("n1", "Conv 3x3"), node("n2", "ReLU"), node("n3", "Conv 3x3")])
    )

    assert len(result.graph.nodes) == 3
    assert codes(result) == [NormalizationCode.FLAGGED_DUPLICATE_LABEL]
    assert result.changes[0].message == (
        "label 'Conv 3x3' is shared by nodes n1, n3 (kept as separate nodes)"
    )


def test_result_serializes_for_logging() -> None:
    result = normalize_graph(build([node("x", " X ")]))

    dumped = json.loads(result.model_dump_json())

    assert dumped["id_map"] == {"x": "n1"}
    assert {c["code"] for c in dumped["changes"]} == {"normalized_text", "renumbered_ids"}
