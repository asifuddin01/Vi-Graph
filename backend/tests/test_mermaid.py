"""Mermaid export. The escaping below was verified against the real Mermaid 12 parser and
renderer in headless Chromium: every label, adversarial ones included, displays literally."""

from pathlib import Path

import pytest

from app.exporters.mermaid import escape_label, to_mermaid
from app.schemas import DiagramGraph, Relation

FIXTURES = Path(__file__).parent / "fixtures"


def diagram(nodes: list[tuple], edges: list[tuple] = ()) -> DiagramGraph:
    """nodes: (id, label[, type[, group_id]]).

    edges: (source, target[, relation[, label[, condition]]]).
    """
    return DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": "flowchart",
            "nodes": [
                {
                    "id": n[0],
                    "label": n[1],
                    "type": n[2] if len(n) > 2 else "module",
                    "group_id": n[3] if len(n) > 3 else None,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e[0],
                    "target": e[1],
                    "relation": e[2] if len(e) > 2 else "flows_to",
                    "label": e[3] if len(e) > 3 else None,
                    "condition": e[4] if len(e) > 4 else None,
                }
                for e in edges
            ],
        }
    )


def test_spec_example() -> None:
    graph = DiagramGraph.model_validate_json((FIXTURES / "graph_v2_example.json").read_text())

    assert to_mermaid(graph) == (
        "flowchart TD\n"
        '    n1(["Input Image"])\n'
        '    n2["CNN Encoder"]\n'
        '    n3["Transformer Encoder"]\n'
        '    n4{{"Feature Fusion"}}\n'
        '    n5(["Classifier"])\n'
        "    n1 --> n2\n"
        "    n1 --> n3\n"
        "    n2 --> n4\n"
        "    n3 --> n4\n"
        "    n4 --> n5\n"
    )


def test_decision_with_labeled_branches() -> None:
    graph = diagram(
        [("d1", "x > 0?", "decision"), ("a", "Path A"), ("b", "Path B")],
        [("d1", "a", "branches_to", "Yes"), ("d1", "b", "branches_to", "No")],
    )

    assert to_mermaid(graph, direction="LR") == (
        "flowchart LR\n"
        '    n1{"x #62; 0?"}\n'
        '    n2["Path A"]\n'
        '    n3["Path B"]\n'
        '    n1 -->|"Yes"| n2\n'
        '    n1 -->|"No"| n3\n'
    )


def test_ids_are_generated_whatever_the_graph_uses() -> None:
    output = to_mermaid(diagram([("end", "End"), ("my node; x", "X")], [("end", "my node; x")]))

    assert '    n1["End"]\n    n2["X"]\n    n1 --> n2\n' in output


@pytest.mark.parametrize(
    ("raw", "escaped"),
    [
        ('say "hi"', "say #34;hi#34;"),
        ("C# & F#", "C#35; #38; F#35;"),
        ("a; b | c", "a#59; b #124; c"),
        ("<b>x</b>", "#60;b#62;x#60;/b#62;"),
        ("`md`", "#96;md#96;"),
        ("A\\nB", "A#92;nB"),
        ("#34;", "#35;34#59;"),  # an entity look-alike stays literal
        ("line\nbreak", "line break"),
        ("Größe ≥ 3 (ok) [x] {y}", "Größe ≥ 3 (ok) [x] {y}"),
    ],
)
def test_escape_label(raw: str, escaped: str) -> None:
    assert escape_label(raw) == escaped


def test_edge_labels_are_escaped() -> None:
    output = to_mermaid(diagram([("a", "A"), ("b", "B")], [("a", "b", "flows_to", 'x | "y"')]))

    assert '    n1 -->|"x #124; #34;y#34;"| n2\n' in output


def test_nested_groups_become_nested_subgraphs() -> None:
    graph = diagram(
        [
            ("blk", "ResNet Block", "group"),
            ("inner", "Inner", "group", "blk"),
            ("conv", "Conv", "module", "inner"),
            ("relu", "ReLU", "operation", "blk"),
            ("head", "Head", "output"),
        ],
        [("conv", "relu"), ("relu", "head"), ("blk", "head", "flows_to", "skip")],
    )

    assert to_mermaid(graph) == (
        "flowchart TD\n"
        '    subgraph n1["ResNet Block"]\n'
        '        subgraph n2["Inner"]\n'
        '            n3["Conv"]\n'
        "        end\n"
        '        n4("ReLU")\n'
        "    end\n"
        '    n5(["Head"])\n'
        "    n3 --> n4\n"
        "    n4 --> n5\n"
        '    n1 -->|"skip"| n5\n'
    )


def test_group_without_members_is_a_plain_node() -> None:
    assert '    n1["Empty Cluster"]\n' in to_mermaid(diagram([("g", "Empty Cluster", "group")]))


def test_relations_are_visible() -> None:
    graph = diagram(
        [("a", "A"), ("b", "B")],
        [
            ("a", "b", "depends_on"),
            ("a", "b", "inherits_from"),
            ("a", "b", "composes", "owns"),
            ("a", "b", "merges_to"),
        ],
    )

    assert to_mermaid(graph).splitlines()[3:] == [
        '    n1 -.->|"depends on"| n2',
        '    n1 -->|"inherits from"| n2',
        '    n1 -->|"owns (composes)"| n2',
        "    n1 --> n2",
    ]


def test_condition_is_shown_when_there_is_no_label() -> None:
    graph = diagram([("a", "A"), ("b", "B")], [("a", "b", "flows_to", None, "x > 0")])

    assert '    n1 -->|"x #62; 0"| n2\n' in to_mermaid(graph)


def test_every_edge_is_emitted_including_parallel_edges_and_self_loops() -> None:
    edges = [("a", "b", r.value) for r in Relation] + [("a", "a")]
    output = to_mermaid(diagram([("a", "A"), ("b", "B")], edges))

    edge_lines = [line for line in output.splitlines() if "-->" in line or "-.->" in line]
    assert len(edge_lines) == len(edges)
    assert edge_lines[-1] == "    n1 --> n1"


def test_output_is_deterministic() -> None:
    graph = DiagramGraph.model_validate_json((FIXTURES / "graph_v2_example.json").read_text())

    assert to_mermaid(graph) == to_mermaid(graph.model_copy(deep=True))
