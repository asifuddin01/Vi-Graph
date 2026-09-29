import json
from pathlib import Path
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from app.schemas import SCHEMA_VERSION, DiagramGraph, DiagramType, NodeType, Relation

FIXTURES = Path(__file__).parent / "fixtures"


def spec_example() -> dict[str, Any]:
    return json.loads((FIXTURES / "graph_v2_example.json").read_text())


def node(node_id: str, type: str = "module", group_id: str | None = None, **extra: Any) -> dict:
    return {"id": node_id, "label": f"Label {node_id}", "type": type, "group_id": group_id, **extra}


def edge(source: str, target: str, relation: str = "flows_to", **extra: Any) -> dict:
    return {"source": source, "target": target, "relation": relation, **extra}


def graph(nodes: list[dict], edges: list[dict] | None = None, **overrides: Any) -> dict:
    return {
        "schema_version": "2.0",
        "diagram_type": "flowchart",
        "nodes": nodes,
        "edges": edges or [],
        **overrides,
    }


def rejection(data: dict) -> str:
    with pytest.raises(ValidationError) as exc_info:
        DiagramGraph.model_validate(data)
    return str(exc_info.value)


# --- valid graphs ---------------------------------------------------------------------


def test_spec_example_is_valid() -> None:
    parsed = DiagramGraph.model_validate(spec_example())

    assert parsed.schema_version == SCHEMA_VERSION
    assert [n.id for n in parsed.nodes] == ["n1", "n2", "n3", "n4", "n5"]
    assert len(parsed.edges) == 5
    assert parsed.nodes[3].type is NodeType.FUSION


def test_json_round_trip_reproduces_spec_example_exactly() -> None:
    text = (FIXTURES / "graph_v2_example.json").read_text()

    dumped = DiagramGraph.model_validate_json(text).model_dump(mode="json")

    assert dumped == spec_example()


def test_schema_version_constant_matches_model() -> None:
    assert SCHEMA_VERSION == "2.0"
    assert get_args(DiagramGraph.model_fields["schema_version"].annotation) == (SCHEMA_VERSION,)


def test_single_node_without_edges_is_valid() -> None:
    DiagramGraph.model_validate(graph([node("n1")], []))


def test_self_loop_is_valid() -> None:
    DiagramGraph.model_validate(graph([node("n1")], [edge("n1", "n1")]))


def test_labels_are_validated_but_not_modified() -> None:
    data = graph([{**node("n1"), "label": "  CNN   Encoder "}])

    parsed = DiagramGraph.model_validate(data)

    assert parsed.nodes[0].label == "  CNN   Encoder "


def test_edge_label_and_condition_are_kept() -> None:
    data = graph(
        [node("d1", type="decision"), node("n2"), node("n3")],
        [
            edge("d1", "n2", "branches_to", label="Yes", condition="x > 0"),
            edge("d1", "n3", "branches_to", label="No", condition=None),
        ],
    )

    parsed = DiagramGraph.model_validate(data)

    assert [(e.label, e.condition) for e in parsed.edges] == [("Yes", "x > 0"), ("No", None)]


@pytest.mark.parametrize("relation", list(Relation))
def test_every_relation_in_vocabulary_is_accepted(relation: Relation) -> None:
    DiagramGraph.model_validate(graph([node("a"), node("b")], [edge("a", "b", relation.value)]))


@pytest.mark.parametrize("diagram_type", list(DiagramType))
def test_every_diagram_type_in_vocabulary_is_accepted(diagram_type: DiagramType) -> None:
    parsed = DiagramGraph.model_validate(graph([node("a")], diagram_type=diagram_type.value))

    assert parsed.diagram_type is diagram_type


def test_nested_groups_are_valid() -> None:
    data = graph(
        [
            node("outer", type="group"),
            node("inner", type="group", group_id="outer"),
            node("conv", group_id="inner"),
            node("relu", type="operation", group_id="inner"),
        ],
        [edge("conv", "relu")],
    )

    parsed = DiagramGraph.model_validate(data)

    assert {n.id: n.group_id for n in parsed.nodes} == {
        "outer": None,
        "inner": "outer",
        "conv": "inner",
        "relu": "inner",
    }


def test_optional_metadata_is_serialized_only_when_set() -> None:
    data = graph([node("n1", bbox=[120, 240, 310, 350], confidence=0.94), node("n2")])

    dumped = DiagramGraph.model_validate(data).model_dump(mode="json")

    assert dumped["nodes"][0]["bbox"] == [120, 240, 310, 350]
    assert dumped["nodes"][0]["confidence"] == 0.94
    assert "bbox" not in dumped["nodes"][1]
    assert "confidence" not in dumped["nodes"][1]


# --- §8 Stage C first-pass rejections -------------------------------------------------


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        DiagramGraph.model_validate_json('{"schema_version": "2.0", "nodes": [')

    assert exc_info.value.errors()[0]["type"] == "json_invalid"


def test_missing_schema_version_is_rejected() -> None:
    data = graph([node("n1")])
    del data["schema_version"]

    assert "schema_version" in rejection(data)


@pytest.mark.parametrize("version", ["1.0", "3.0", "2", 2.0, "", None])
def test_unknown_schema_version_is_rejected(version: object) -> None:
    message = rejection(graph([node("n1")], schema_version=version))

    assert "unsupported schema_version" in message


def test_empty_node_list_is_rejected() -> None:
    assert "nodes" in rejection(graph([]))


def test_missing_edges_key_is_rejected() -> None:
    data = graph([node("n1")])
    del data["edges"]

    assert "edges" in rejection(data)


def test_edge_to_nonexistent_node_is_rejected_with_ids() -> None:
    message = rejection(graph([node("n1"), node("n3")], [edge("n1", "n3"), edge("n3", "n9")]))

    assert "edge #1 'n3->n9' references node id 'n9', which does not exist" in message


def test_edge_with_both_ends_missing_reports_both() -> None:
    message = rejection(graph([node("n1")], [edge("x", "y")]))

    assert "node id 'x'" in message
    assert "node id 'y'" in message


def test_duplicate_node_ids_are_rejected() -> None:
    message = rejection(graph([node("n1"), node("n2"), node("n1")]))

    assert "duplicate node id 'n1' is used by 2 nodes" in message


@pytest.mark.parametrize("label", ["", "   ", "\n\t"])
def test_blank_node_label_is_rejected(label: str) -> None:
    message = rejection(graph([{**node("n1"), "label": label}]))

    assert "label" in message


@pytest.mark.parametrize("field", ["id", "label", "type"])
def test_required_node_fields_are_enforced(field: str) -> None:
    bad_node = node("n1")
    del bad_node[field]

    assert field in rejection(graph([bad_node]))


def test_non_string_node_id_is_rejected() -> None:
    assert "id" in rejection(graph([{**node("n1"), "id": 1}]))


def test_unknown_node_type_is_rejected() -> None:
    assert "type" in rejection(graph([node("n1", type="layer")]))


@pytest.mark.parametrize("diagram_type", ["cnn", "Neural Network", ""])
def test_unknown_diagram_type_is_rejected(diagram_type: str) -> None:
    assert "diagram_type" in rejection(graph([node("n1")], diagram_type=diagram_type))


def test_unknown_relation_is_rejected() -> None:
    assert "relation" in rejection(graph([node("a"), node("b")], [edge("a", "b", "calls")]))


@pytest.mark.parametrize(
    "data",
    [
        graph([node("n1")], extra_key=True),
        graph([node("n1", description="extra")]),
        graph([node("a"), node("b")], [edge("a", "b", weight=1)]),
    ],
    ids=["graph", "node", "edge"],
)
def test_unknown_fields_are_rejected(data: dict) -> None:
    assert "Extra inputs are not permitted" in rejection(data)


# --- group_id rules -------------------------------------------------------------------


def test_group_id_to_nonexistent_node_is_rejected() -> None:
    message = rejection(graph([node("n1", group_id="g9")]))

    assert "node 'n1' has group_id 'g9', which is not an existing node id" in message


def test_group_id_pointing_to_itself_is_rejected() -> None:
    message = rejection(graph([node("g1", type="group", group_id="g1")]))

    assert "node 'g1' has group_id pointing to itself" in message


def test_group_id_to_non_group_node_is_rejected() -> None:
    message = rejection(graph([node("block", type="module"), node("n1", group_id="block")]))

    assert "node 'block' has type 'module' instead of 'group'" in message


def test_group_containment_cycle_is_rejected() -> None:
    message = rejection(
        graph([node("g1", type="group", group_id="g2"), node("g2", type="group", group_id="g1")])
    )

    assert "group_id containment cycle: g1 -> g2 -> g1" in message
    assert message.count("containment cycle") == 1


# --- optional metadata ----------------------------------------------------------------


def test_reversed_bbox_is_rejected() -> None:
    assert "bbox" in rejection(graph([node("n1", bbox=[300, 240, 120, 350])]))


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
def test_confidence_out_of_range_is_rejected(confidence: float) -> None:
    assert "confidence" in rejection(graph([node("n1", confidence=confidence)]))


# --- error reporting ------------------------------------------------------------------


def test_all_structural_problems_are_reported_together() -> None:
    message = rejection(
        graph(
            [node("n1"), node("n1"), node("n2", group_id="missing")],
            [edge("n1", "n7")],
        )
    )

    assert "duplicate node id 'n1'" in message
    assert "'n1->n7' references node id 'n7'" in message
    assert "group_id 'missing'" in message
