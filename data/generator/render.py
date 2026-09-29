"""Render a ground-truth graph as a diagram image with randomized visual style (spec §13).

Rendering uses Graphviz. Per sample it varies the theme (background, fills, colours,
font), node shapes, arrowheads, line width, edge routing, spacing, resolution, and the
layout family. Two rules keep the image faithful to its ground truth:

- Groups need a layout that draws clusters, so graphs with groups only get the layered or
  force layouts (twopi/circo ignore clusters and would hide the nesting).
- UML relations get their UML arrowheads, since that is the only visual evidence for them.

Only DejaVu fonts are used, and every parameter is recorded (``RenderParams``), so a
sample can be re-rendered exactly on a machine with the same Graphviz version.
"""

from __future__ import annotations

import io
import random
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image
from pydantic import BaseModel

from app.exporters.graphviz import quote
from app.schemas import DiagramGraph, Node, NodeType, Relation

LAYOUTS = ["layered_tb", "layered_lr", "radial", "circular", "force"]
CLUSTER_LAYOUTS = {"layered_tb", "layered_lr", "force"}
_ENGINES = {
    "layered_tb": "dot",
    "layered_lr": "dot",
    "radial": "twopi",
    "circular": "circo",
    "force": "fdp",
}
FONTS = ["DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono"]
RENDER_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class Theme:
    background: str
    fills: tuple[str, ...]  # one per node type, cycled; empty = unfilled
    border: str
    text: str
    edge: str
    fonts: tuple[str, ...]
    rounded: bool = False
    penwidth: tuple[float, float] = (1.0, 1.6)
    cluster_fill: str | None = None


THEMES: dict[str, Theme] = {
    "classic": Theme("white", (), "black", "black", "black", ("DejaVu Serif", "DejaVu Sans")),
    "pastel": Theme(
        "white",
        ("#dbeafe", "#dcfce7", "#fef3c7", "#fce7f3", "#ede9fe", "#e0f2fe"),
        "#475569",
        "#0f172a",
        "#475569",
        ("DejaVu Sans",),
        rounded=True,
        cluster_fill="#f8fafc",
    ),
    "dark": Theme(
        "#1e1e1e",
        ("#2d2d2d", "#3a3a3a"),
        "#a3a3a3",
        "#f5f5f5",
        "#d4d4d4",
        ("DejaVu Sans",),
        rounded=True,
        cluster_fill="#262626",
    ),
    "blueprint": Theme(
        "#1e3a8a", (), "#ffffff", "#ffffff", "#e0e7ff", ("DejaVu Sans Mono",), penwidth=(1.2, 1.8)
    ),
    "sketch": Theme(
        "white",
        (),
        "#222222",
        "#222222",
        "#222222",
        ("DejaVu Sans Mono",),
        rounded=True,
        penwidth=(1.8, 2.6),
    ),
    "corporate": Theme(
        "#f8fafc",
        ("#e2e8f0", "#cbd5e1", "#dbeafe"),
        "#334155",
        "#0f172a",
        "#334155",
        ("DejaVu Sans",),
        cluster_fill="#f1f5f9",
    ),
    "paper": Theme(
        "#fdf6e3",
        ("#fffbeb", "#fef3c7"),
        "#78350f",
        "#451a03",
        "#78350f",
        ("DejaVu Serif",),
    ),
    "vivid": Theme(
        "white",
        ("#93c5fd", "#6ee7b7", "#fcd34d", "#fca5a5", "#c4b5fd", "#f9a8d4"),
        "#111827",
        "#111827",
        "#111827",
        ("DejaVu Sans",),
        rounded=True,
        penwidth=(1.2, 2.0),
        cluster_fill="#f9fafb",
    ),
}

# Plausible shapes per node type; decisions are always diamonds (their visual cue).
_SHAPES: dict[NodeType, list[str]] = {
    NodeType.INPUT: ["box", "ellipse", "parallelogram", "box"],
    NodeType.OUTPUT: ["box", "ellipse", "box", "octagon"],
    NodeType.MODULE: ["box"],
    NodeType.OPERATION: ["box", "ellipse", "box"],
    NodeType.DECISION: ["diamond"],
    NodeType.FUSION: ["circle", "ellipse", "hexagon", "box"],
    NodeType.UNKNOWN: ["box"],
}

# Level-dependent font size (§14: large text at level 1, tiny text at level 4).
_FONT_SIZES = {1: (14, 18), 2: (11, 15), 3: (9, 12), 4: (7, 10)}


class RenderParams(BaseModel):
    layout: str
    engine: str
    theme: str
    font: str
    font_size: float
    dpi: int
    splines: str
    arrowhead: str
    penwidth: float
    node_sep: float
    rank_sep: float
    shapes: dict[str, str]  # node type → Graphviz shape
    type_fills: dict[str, str]  # node type → fill colour ("" = unfilled)


@dataclass
class RenderedImage:
    png: bytes
    width: int
    height: int
    dot: str


def sample_params(
    rng: random.Random,
    graph: DiagramGraph,
    level: int,
    layouts: list[str],
    themes: list[str],
) -> RenderParams:
    has_groups = any(node.type is NodeType.GROUP for node in graph.nodes)
    candidates = [layout for layout in layouts if not has_groups or layout in CLUSTER_LAYOUTS]
    if not candidates:
        raise ValueError(f"no layout in {layouts} can draw groups")
    layout = rng.choice(candidates)
    theme_name = rng.choice(themes)
    theme = THEMES[theme_name]
    fills = list(theme.fills)
    rng.shuffle(fills)
    types = [t for t in NodeType if t is not NodeType.GROUP]
    low, high = _FONT_SIZES[level]
    dense = level >= 3
    # Orthogonal routing can drop edge labels, which would hide ground truth.
    has_edge_text = any(e.label or e.condition for e in graph.edges)
    layered_splines = ["spline", "polyline", "spline"] + ([] if has_edge_text else ["ortho"])
    return RenderParams(
        layout=layout,
        engine=_ENGINES[layout],
        theme=theme_name,
        font=rng.choice(theme.fonts),
        font_size=round(rng.uniform(low, high), 1),
        dpi=rng.choice([96, 110, 120, 144]),
        splines=rng.choice(layered_splines)
        if layout.startswith("layered")
        else rng.choice(["spline", "line"]),
        arrowhead=rng.choice(["normal", "vee", "normal", "open", "empty"]),
        penwidth=round(rng.uniform(*theme.penwidth), 2),
        node_sep=round(rng.uniform(0.15, 0.35) if dense else rng.uniform(0.3, 0.7), 2),
        rank_sep=round(rng.uniform(0.25, 0.45) if dense else rng.uniform(0.4, 0.9), 2),
        shapes={t.value: rng.choice(_SHAPES[t]) for t in types},
        type_fills={t.value: fills[i % len(fills)] if fills else "" for i, t in enumerate(types)},
    )


def to_styled_dot(graph: DiagramGraph, params: RenderParams) -> str:
    theme = THEMES[params.theme]
    children: dict[str | None, list[Node]] = defaultdict(list)
    for node in graph.nodes:
        children[node.group_id].append(node)

    graph_attrs = [
        f'bgcolor="{theme.background}"',
        f'fontname="{params.font}"',
        f"fontsize={params.font_size}",
        f'fontcolor="{theme.text}"',
        f"dpi={params.dpi}",
        f"splines={params.splines}",
        f"nodesep={params.node_sep}",
        'size="16,16"',
        "pad=0.25",
        "overlap=false",
        "sep=0.3",
    ]
    if params.engine == "dot":
        graph_attrs += [
            f"rankdir={'TB' if params.layout == 'layered_tb' else 'LR'}",
            f"ranksep={params.rank_sep}",
        ]
    if params.engine == "twopi":
        sources = {n.id for n in graph.nodes} - {e.target for e in graph.edges}
        root = next(
            (n.id for n in graph.nodes if n.id in sources and n.type is not NodeType.GROUP),
            graph.nodes[0].id,
        )
        graph_attrs += [f"root={quote(root)}", f"ranksep={params.rank_sep + 0.6}"]

    lines = [
        "digraph G {",
        f"  graph [{', '.join(graph_attrs)}];",
        f'  node [fontname="{params.font}", fontsize={params.font_size}, '
        f'fontcolor="{theme.text}", color="{theme.border}", penwidth={params.penwidth}, '
        'margin="0.15,0.06"];',
        f'  edge [fontname="{params.font}", fontsize={max(6.0, params.font_size - 2)}, '
        f'fontcolor="{theme.text}", color="{theme.edge}", penwidth={params.penwidth}, '
        f"arrowhead={params.arrowhead}];",
    ]

    def emit(node: Node, depth: int) -> None:
        indent = "  " * depth
        if node.type is NodeType.GROUP:
            style = "rounded,filled" if theme.cluster_fill else "rounded,dashed"
            fill = f', fillcolor="{theme.cluster_fill}"' if theme.cluster_fill else ""
            lines.append(f"{indent}subgraph {quote('cluster_' + node.id)} {{")
            lines.append(
                f'{indent}  graph [label={quote(node.label)}, style="{style}", '
                f'color="{theme.border}"{fill}, labeljust=l];'
            )
            for member in children[node.id]:
                emit(member, depth + 1)
            lines.append(f"{indent}}}")
            return
        shape = params.shapes[node.type.value]
        fill = params.type_fills[node.type.value]
        styles = [
            s
            for s in (
                "filled" if fill else "",
                "rounded" if theme.rounded and shape == "box" else "",
            )
            if s
        ]
        attrs = [f"label={quote(node.label)}", f"shape={shape}"]
        if styles:
            attrs.append(f'style="{",".join(styles)}"')
        if fill:
            attrs.append(f'fillcolor="{fill}"')
        if shape == "circle":
            attrs.append("fixedsize=false")
        lines.append(f"{indent}{quote(node.id)} [{', '.join(attrs)}];")

    for node in children[None]:
        emit(node, 1)
    for edge in graph.edges:
        attrs = _edge_style(edge.relation)
        text = edge.label if edge.label is not None else edge.condition
        if text:
            attrs.append(f"label={quote(text)}")
        suffix = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f"  {quote(edge.source)} -> {quote(edge.target)}{suffix};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _edge_style(relation: Relation) -> list[str]:
    """UML relations get UML notation; dependencies are dashed everywhere."""
    if relation is Relation.INHERITS_FROM:
        return ["arrowhead=empty"]
    if relation is Relation.COMPOSES:
        return ["dir=back", "arrowtail=diamond"]
    if relation is Relation.AGGREGATES:
        return ["dir=back", "arrowtail=odiamond"]
    if relation is Relation.DEPENDS_ON:
        return ["style=dashed", "arrowhead=vee"]
    return []


def render(graph: DiagramGraph, params: RenderParams) -> RenderedImage:
    dot = to_styled_dot(graph, params)
    executable = shutil.which(params.engine)
    if executable is None:
        raise RuntimeError(f"Graphviz '{params.engine}' is not installed")
    result = subprocess.run(
        [executable, "-Tpng"],
        input=dot.encode("utf-8"),
        capture_output=True,
        timeout=RENDER_TIMEOUT_SECONDS,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        message = result.stderr.decode(errors="replace").strip()[:300]
        raise RuntimeError(f"Graphviz ({params.engine}) failed: {message}")
    with Image.open(io.BytesIO(result.stdout)) as image:
        width, height = image.size
    return RenderedImage(png=result.stdout, width=width, height=height, dot=dot)


@lru_cache
def graphviz_version() -> str:
    dot = shutil.which("dot")
    if dot is None:
        return "not installed"
    out = subprocess.run([dot, "-V"], capture_output=True, check=False)
    return out.stderr.decode(errors="replace").strip()
