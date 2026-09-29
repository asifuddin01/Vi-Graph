import copy
from typing import Any

import pytest

from app.pipeline.repair import RepairCode, RepairError, RepairFix, repair_graph
from app.schemas import DiagramGraph


def node(node_id: Any, label: Any = None, type: Any = "module", **extra: Any) -> dict:
    return {
        "id": node_id,
        "label": f"Label {node_id}" if label is None else label,
        "type": type,
        **extra,
    }


def edge(source: Any, target: Any, relation: Any = "flows_to", **extra: Any) -> dict:
    return {"source": source, "target": target, "relation": relation, **extra}


def graph(nodes: list, edges: list | None = None, **overrides: Any) -> dict:
    return {
        "schema_version": "2.0",
        "diagram_type": "flowchart",
        "nodes": nodes,
        "edges": [] if edges is None else edges,
        **overrides,
    }


def repair(data: dict) -> tuple[DiagramGraph, list[RepairFix]]:
    repaired, fixes = repair_graph(data)
    return DiagramGraph.model_validate(repaired), fixes


def codes(fixes: list[RepairFix]) -> list[RepairCode]:
    return [fix.code for fix in fixes]


# --- general --------------------------------------------------------------------------


def test_valid_graph_needs_no_fixes() -> None:
    parsed, fixes = repair(graph([node("a"), node("b")], [edge("a", "b", label="Yes")]))

    assert fixes == []
    assert parsed.edges[0].label == "Yes"


def test_input_is_not_modified() -> None:
    data = graph(
        [node(1), node("b", type="Layer"), "junk"], [edge(1, "b"), edge("b", "zz")], extra=True
    )
    snapshot = copy.deepcopy(data)

    repair_graph(data)

    assert data == snapshot


def test_unknown_fields_are_dropped_at_every_level() -> None:
    data = graph([node("a", description="x")], [edge("a", "a", weight=2)], notes="hi")

    parsed, fixes = repair(data)

    assert codes(fixes) == [RepairCode.DROPPED_UNKNOWN_FIELD] * 3
    assert [f.message for f in fixes] == [
        "graph: dropped unknown field 'notes'",
        "nodes[0]: dropped unknown field 'description'",
        "edges[0]: dropped unknown field 'weight'",
    ]


@pytest.mark.parametrize("version", ["1.0", 2.0, None])
def test_schema_version_is_set(version: object) -> None:
    parsed, fixes = repair(graph([node("a")], schema_version=version))

    assert parsed.schema_version == "2.0"
    assert codes(fixes) == [RepairCode.SET_SCHEMA_VERSION]


def test_missing_schema_version_is_set() -> None:
    data = graph([node("a")])
    del data["schema_version"]

    _, fixes = repair(data)

    assert fixes[0].message == "schema_version missing replaced with '2.0'"


# --- vocabulary -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected", "code"),
    [
        ("Neural Network", "neural_network", RepairCode.MAPPED_VALUE),
        ("system-architecture", "system_architecture", RepairCode.MAPPED_VALUE),
        ("cnn", "other", RepairCode.DEFAULTED_VALUE),
        (None, "other", RepairCode.DEFAULTED_VALUE),
    ],
)
def test_diagram_type_is_mapped_or_defaulted(
    value: object, expected: str, code: RepairCode
) -> None:
    parsed, fixes = repair(graph([node("a")], diagram_type=value))

    assert parsed.diagram_type == expected
    assert codes(fixes) == [code]


@pytest.mark.parametrize(
    ("value", "expected", "code"),
    [
        ("Module", "module", RepairCode.MAPPED_VALUE),
        ("  OUTPUT ", "output", RepairCode.MAPPED_VALUE),
        ("layer", "unknown", RepairCode.DEFAULTED_VALUE),
        (3, "unknown", RepairCode.DEFAULTED_VALUE),
    ],
)
def test_node_type_is_mapped_or_defaulted(value: object, expected: str, code: RepairCode) -> None:
    parsed, fixes = repair(graph([node("a", type=value)]))

    assert parsed.nodes[0].type == expected
    assert codes(fixes) == [code]


def test_missing_node_type_becomes_unknown() -> None:
    data = graph([node("a")])
    del data["nodes"][0]["type"]

    parsed, fixes = repair(data)

    assert parsed.nodes[0].type == "unknown"
    assert fixes[0].message == "nodes[0] ('a').type: missing is not allowed; set to 'unknown'"


@pytest.mark.parametrize(
    ("value", "expected", "code"),
    [
        ("flows to", "flows_to", RepairCode.MAPPED_VALUE),
        ("DEPENDS-ON", "depends_on", RepairCode.MAPPED_VALUE),
        ("calls", "unknown", RepairCode.DEFAULTED_VALUE),
    ],
)
def test_relation_is_mapped_or_defaulted(value: str, expected: str, code: RepairCode) -> None:
    parsed, fixes = repair(graph([node("a"), node("b")], [edge("a", "b", relation=value)]))

    assert parsed.edges[0].relation == expected
    assert codes(fixes) == [code]


# --- nodes ----------------------------------------------------------------------------


def test_numeric_ids_are_converted_and_edges_follow() -> None:
    parsed, fixes = repair(graph([node(1), node(2)], [edge(1, 2)]))

    assert [n.id for n in parsed.nodes] == ["1", "2"]
    assert (parsed.edges[0].source, parsed.edges[0].target) == ("1", "2")
    assert set(codes(fixes)) == {RepairCode.COERCED_TO_STRING}


def test_numeric_label_is_converted() -> None:
    parsed, _ = repair(graph([node("dense", label=1024)]))

    assert parsed.nodes[0].label == "1024"


@pytest.mark.parametrize(
    "bad_node",
    [
        {"label": "No id", "type": "module"},
        node("  "),
        node(True),
        node("a", label="  "),
        node("a", label=["x"]),
        "not an object",
    ],
    ids=["missing-id", "blank-id", "bool-id", "blank-label", "list-label", "not-object"],
)
def test_nodes_without_usable_id_or_label_are_dropped(bad_node: Any) -> None:
    parsed, fixes = repair(graph([node("keep"), bad_node]))

    assert [n.id for n in parsed.nodes] == ["keep"]
    assert RepairCode.DROPPED_NODE in codes(fixes)


def test_duplicate_node_keeps_the_first() -> None:
    parsed, fixes = repair(graph([node("a", label="First"), node("a", label="Second")]))

    assert [n.label for n in parsed.nodes] == ["First"]
    assert codes(fixes) == [RepairCode.DROPPED_DUPLICATE_NODE]


def test_dropped_invalid_node_does_not_block_a_later_valid_one_with_same_id() -> None:
    parsed, _ = repair(graph([node("a", label=""), node("a", label="Real")]))

    assert [n.label for n in parsed.nodes] == ["Real"]


@pytest.mark.parametrize("nodes", [None, "n1", {"id": "a"}], ids=["null", "string", "object"])
def test_nodes_that_are_not_a_list_cannot_be_repaired(nodes: object) -> None:
    with pytest.raises(RepairError, match="not a list"):
        repair_graph(graph(nodes))  # type: ignore[arg-type]


def test_missing_nodes_cannot_be_repaired() -> None:
    data = graph([])
    del data["nodes"]

    with pytest.raises(RepairError, match="'nodes' is missing"):
        repair_graph(data)


def test_no_salvageable_nodes_cannot_be_repaired() -> None:
    with pytest.raises(RepairError, match="no valid nodes remain"):
        repair_graph(graph([node("a", label=""), "junk"]))


def test_invalid_metadata_is_dropped_and_valid_metadata_kept() -> None:
    data = graph(
        [
            node("a", bbox=[10, 10, 5, 50], confidence=1.7),
            node("b", bbox=[0, 0, 20, 20], confidence=0.5),
        ]
    )

    parsed, fixes = repair(data)

    assert parsed.nodes[0].bbox is None and parsed.nodes[0].confidence is None
    assert parsed.nodes[1].bbox == (0, 0, 20, 20) and parsed.nodes[1].confidence == 0.5
    assert codes(fixes) == [RepairCode.DROPPED_METADATA] * 2


# --- groups ---------------------------------------------------------------------------


def test_group_id_pointing_to_itself_is_cleared() -> None:
    parsed, fixes = repair(graph([node("g", type="group", group_id="g")]))

    assert parsed.nodes[0].group_id is None
    assert codes(fixes) == [RepairCode.CLEARED_GROUP_ID]


@pytest.mark.parametrize("group_id", ["ghost", "", "  "], ids=["nonexistent", "empty", "blank"])
def test_unusable_group_id_is_cleared(group_id: str) -> None:
    parsed, fixes = repair(graph([node("a", group_id=group_id)]))

    assert parsed.nodes[0].group_id is None
    assert codes(fixes) == [RepairCode.CLEARED_GROUP_ID]


def test_numeric_group_id_is_converted() -> None:
    parsed, _ = repair(graph([node(7, type="group"), node("a", group_id=7)]))

    assert parsed.nodes[1].group_id == "7"


def test_container_that_is_not_a_group_is_retyped() -> None:
    parsed, fixes = repair(
        graph(
            [node("block", type="module"), node("a", group_id="block"), node("b", group_id="block")]
        )
    )

    assert parsed.nodes[0].type == "group"
    assert codes(fixes) == [RepairCode.RETYPED_GROUP_CONTAINER]  # reported once per container


def test_group_cycle_is_broken_at_the_first_node() -> None:
    parsed, fixes = repair(
        graph([node("g1", type="group", group_id="g2"), node("g2", type="group", group_id="g1")])
    )

    assert {n.id: n.group_id for n in parsed.nodes} == {"g1": None, "g2": "g1"}
    assert codes(fixes) == [RepairCode.BROKE_GROUP_CYCLE]
    assert fixes[0].message == "group_id cycle g1 -> g2 -> g1; cleared group_id of 'g1'"


# --- edges ----------------------------------------------------------------------------


@pytest.mark.parametrize("edges", [None, "n1->n2", {"source": "a"}], ids=["null", "str", "obj"])
def test_edges_that_are_not_a_list_become_empty(edges: object) -> None:
    data = graph([node("a")])
    data["edges"] = edges

    parsed, fixes = repair(data)

    assert parsed.edges == []
    assert codes(fixes) == [RepairCode.REPLACED_EDGES]


def test_missing_edges_become_empty() -> None:
    data = graph([node("a")])
    del data["edges"]

    parsed, fixes = repair(data)

    assert parsed.edges == []
    assert fixes[0].message == "'edges' is missing; set to []"


def test_dangling_edges_are_dropped() -> None:
    parsed, fixes = repair(
        graph([node("a"), node("b")], [edge("a", "b"), edge("a", "n9"), edge("x", "y")])
    )

    assert [(e.source, e.target) for e in parsed.edges] == [("a", "b")]
    assert [f.message for f in fixes] == [
        "edges[1]: target 'n9' not an existing node; dropped",
        "edges[2]: source 'x' and target 'y' not an existing node; dropped",
    ]


def test_edges_to_dropped_nodes_are_dropped() -> None:
    parsed, fixes = repair(graph([node("a"), node("b", label="")], [edge("a", "b")]))

    assert parsed.edges == []
    assert codes(fixes) == [RepairCode.DROPPED_NODE, RepairCode.DROPPED_EDGE]


def test_non_object_edge_is_dropped() -> None:
    parsed, fixes = repair(graph([node("a")], ["a->a"]))

    assert parsed.edges == []
    assert codes(fixes) == [RepairCode.DROPPED_EDGE]


def test_edge_label_types_are_fixed() -> None:
    parsed, fixes = repair(
        graph([node("a"), node("b")], [edge("a", "b", label=1, condition={"x": 0})])
    )

    assert (parsed.edges[0].label, parsed.edges[0].condition) == ("1", None)
    assert codes(fixes) == [RepairCode.COERCED_TO_STRING, RepairCode.CLEARED_VALUE]
