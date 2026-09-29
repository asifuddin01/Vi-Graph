"""Canonical graph → Mermaid flowchart (spec §10).

- Input is always a validated ``DiagramGraph``, never free text.
- Mermaid ids are generated here (n1..nk in node order), so output is deterministic and
  safe whatever ids the graph uses.
- Every label is quoted, with characters that Mermaid or HTML would interpret replaced
  by Mermaid entity codes (``#34;`` etc.) — including edge labels (§29).
- Groups with members become (nested) ``subgraph`` blocks; edges may target a subgraph.
- Every edge is emitted, parallel edges and self-loops included: topology is preserved.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Literal

from app.schemas import DiagramGraph, Edge, Node, NodeType, Relation

Direction = Literal["TD", "LR", "BT", "RL"]

# Characters with meaning to Mermaid's parser, its markdown strings, or HTML labels.
_ESCAPES = str.maketrans(
    {
        "#": "#35;",
        '"': "#34;",
        "&": "#38;",
        "<": "#60;",
        ">": "#62;",
        "|": "#124;",
        ";": "#59;",
        "`": "#96;",
        "\\": "#92;",  # backslash: Mermaid reads a literal backslash-n as a line break
        "\n": " ",
        "\r": " ",
    }
)

# (open, close) delimiters per node type; the label goes quoted in between.
_SHAPES: dict[NodeType, tuple[str, str]] = {
    NodeType.INPUT: ("([", "])"),  # stadium
    NodeType.OUTPUT: ("([", "])"),
    NodeType.MODULE: ("[", "]"),  # rectangle
    NodeType.OPERATION: ("(", ")"),  # rounded
    NodeType.DECISION: ("{", "}"),  # rhombus
    NodeType.FUSION: ("{{", "}}"),  # hexagon (a circle grows with long labels)
    NodeType.GROUP: ("[", "]"),  # a group with no members is drawn as a plain node
    NodeType.UNKNOWN: ("[", "]"),
}

# Relations drawn as plain flow; others show their name so their meaning isn't lost.
_PLAIN_RELATIONS = {
    Relation.FLOWS_TO,
    Relation.BRANCHES_TO,
    Relation.MERGES_TO,
    Relation.UNKNOWN,
}


def escape_label(text: str) -> str:
    return text.translate(_ESCAPES)


def to_mermaid(graph: DiagramGraph, direction: Direction = "TD") -> str:
    ids = {node.id: f"n{index}" for index, node in enumerate(graph.nodes, start=1)}
    children: dict[str | None, list[Node]] = defaultdict(list)
    for node in graph.nodes:
        children[node.group_id].append(node)

    lines = [f"flowchart {direction}"]

    def emit(node: Node, depth: int) -> None:
        indent = "    " * depth
        label = escape_label(node.label)
        members = children.get(node.id, [])
        if node.type is NodeType.GROUP and members:
            lines.append(f'{indent}subgraph {ids[node.id]}["{label}"]')
            for member in members:
                emit(member, depth + 1)
            lines.append(f"{indent}end")
        else:
            open_, close = _SHAPES[node.type]
            lines.append(f'{indent}{ids[node.id]}{open_}"{label}"{close}')

    for node in children[None]:
        emit(node, 1)
    for edge in graph.edges:
        lines.append(f"    {_edge_line(edge, ids)}")
    return "\n".join(lines) + "\n"


def _edge_line(edge: Edge, ids: dict[str, str]) -> str:
    arrow = "-.->" if edge.relation is Relation.DEPENDS_ON else "-->"
    text = edge.label if edge.label is not None else edge.condition
    if edge.relation not in _PLAIN_RELATIONS:
        relation = edge.relation.value.replace("_", " ")
        text = f"{text} ({relation})" if text else relation
    source, target = ids[edge.source], ids[edge.target]
    if not text:
        return f"{source} {arrow} {target}"
    return f'{source} {arrow}|"{escape_label(text)}"| {target}'
