"""Canonical graph → Graphviz DOT → SVG / PNG / PDF (spec §28 exports).

Graphviz is an optional system dependency (§6): without the ``dot`` binary, rendering
raises ``RenderUnavailable`` and only the JSON and Mermaid exports work.

- Ids are generated here (n1..nk); every label is quoted and escaped, including Graphviz's
  own label escapes (\\n, \\N, \\G, ...), so labels always render literally.
- Groups with members become nested clusters. Graphviz can't attach edges to a cluster, so
  an invisible anchor node inside it takes the edge, clipped at the cluster border
  (compound=true with lhead/ltail).
- ``dot`` runs as a subprocess with no shell, a timeout, and a node limit.
"""

from __future__ import annotations

import shutil
import subprocess
from collections import defaultdict
from typing import Literal

from app.schemas import DiagramGraph, Edge, Node, NodeType, Relation

RenderFormat = Literal["svg", "png", "pdf"]

MAX_RENDER_NODES = 500
RENDER_TIMEOUT_SECONDS = 20

# Node attributes per type; they mirror the Mermaid export's shapes.
_NODE_STYLE: dict[NodeType, str] = {
    NodeType.INPUT: 'shape=box, style="rounded,filled", fillcolor="#e0f2fe"',
    NodeType.OUTPUT: 'shape=box, style="rounded,filled", fillcolor="#d1fae5"',
    NodeType.MODULE: 'shape=box, style=filled, fillcolor="#ffffff"',
    NodeType.OPERATION: 'shape=box, style="rounded,filled", fillcolor="#e0e7ff"',
    NodeType.DECISION: 'shape=diamond, style=filled, fillcolor="#fde68a"',
    NodeType.FUSION: 'shape=hexagon, style=filled, fillcolor="#ede9fe"',
    NodeType.GROUP: 'shape=box, style="dashed"',  # a group without members
    NodeType.UNKNOWN: 'shape=box, style="dashed,filled", fillcolor="#f4f4f5"',
}

_PLAIN_RELATIONS = {Relation.FLOWS_TO, Relation.BRANCHES_TO, Relation.MERGES_TO, Relation.UNKNOWN}


class RenderUnavailable(RuntimeError):
    """Graphviz (the ``dot`` binary) is not installed."""


class RenderError(RuntimeError):
    """Graphviz failed to render the graph."""


def quote(text: str) -> str:
    """A DOT double-quoted string whose content is shown literally."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + " ".join(escaped.split()) + '"'


def to_dot(graph: DiagramGraph) -> str:
    ids = {node.id: f"n{index}" for index, node in enumerate(graph.nodes, start=1)}
    children: dict[str | None, list[Node]] = defaultdict(list)
    for node in graph.nodes:
        children[node.group_id].append(node)
    clusters = {
        node.id for node in graph.nodes if node.type is NodeType.GROUP and children[node.id]
    }

    lines = [
        "digraph vigraph {",
        "  graph [rankdir=TB, compound=true, nodesep=0.45, ranksep=0.55, "
        'fontname="Helvetica", fontsize=12, bgcolor="white"];',
        '  node [fontname="Helvetica", fontsize=12, margin="0.18,0.08", color="#52525b"];',
        '  edge [fontname="Helvetica", fontsize=10, color="#52525b", arrowsize=0.8];',
    ]

    def emit(node: Node, depth: int) -> None:
        indent = "  " * depth
        if node.id in clusters:
            lines.append(f"{indent}subgraph cluster_{ids[node.id]} {{")
            lines.append(
                f'{indent}  label={quote(node.label)}; style=dashed; color="#a1a1aa"; labeljust=l;'
            )
            # Invisible anchor for edges that start or end at this group.
            lines.append(f"{indent}  {ids[node.id]} [shape=point, style=invis, width=0.01];")
            for member in children[node.id]:
                emit(member, depth + 1)
            lines.append(f"{indent}}}")
        else:
            lines.append(
                f"{indent}{ids[node.id]} [label={quote(node.label)}, {_NODE_STYLE[node.type]}];"
            )

    for node in children[None]:
        emit(node, 1)
    for edge in graph.edges:
        lines.append(f"  {_edge_line(edge, ids, clusters)}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _edge_line(edge: Edge, ids: dict[str, str], clusters: set[str]) -> str:
    text = edge.label if edge.label is not None else edge.condition
    if edge.relation not in _PLAIN_RELATIONS:
        relation = edge.relation.value.replace("_", " ")
        text = f"{text} ({relation})" if text else relation
    attrs = []
    if text:
        attrs.append(f"label={quote(text)}")
    if edge.relation is Relation.DEPENDS_ON:
        attrs.append("style=dashed")
    if edge.source in clusters:
        attrs.append(f"ltail=cluster_{ids[edge.source]}")
    if edge.target in clusters:
        attrs.append(f"lhead=cluster_{ids[edge.target]}")
    suffix = f" [{', '.join(attrs)}]" if attrs else ""
    return f"{ids[edge.source]} -> {ids[edge.target]}{suffix};"


def graphviz_available() -> bool:
    return shutil.which("dot") is not None


def render(graph: DiagramGraph, fmt: RenderFormat) -> bytes:
    if len(graph.nodes) > MAX_RENDER_NODES:
        raise RenderError(f"graphs over {MAX_RENDER_NODES} nodes are not rendered")
    dot = shutil.which("dot")
    if dot is None:
        raise RenderUnavailable("Graphviz is not installed; SVG/PNG/PDF export is unavailable")
    args = [dot, f"-T{fmt}"]
    if fmt == "png":
        args.append("-Gdpi=144")
    try:
        result = subprocess.run(
            args,
            input=to_dot(graph).encode("utf-8"),
            capture_output=True,
            timeout=RENDER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError("Graphviz timed out") from exc
    if result.returncode != 0 or not result.stdout:
        raise RenderError(
            f"Graphviz failed: {result.stderr.decode(errors='replace').strip()[:300]}"
        )
    return result.stdout
