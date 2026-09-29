import html
import re
from pathlib import Path

import pytest

from app.exporters import graphviz
from app.exporters.graphviz import (
    RenderError,
    RenderUnavailable,
    graphviz_available,
    quote,
    render,
    to_dot,
)
from app.schemas import DiagramGraph

FIXTURES = Path(__file__).parent / "fixtures"
needs_graphviz = pytest.mark.skipif(not graphviz_available(), reason="Graphviz not installed")


def spec_example() -> DiagramGraph:
    return DiagramGraph.model_validate_json((FIXTURES / "graph_v2_example.json").read_text())


def diagram(nodes: list[tuple], edges: list[tuple] = ()) -> DiagramGraph:
    """nodes: (id, label[, type[, group_id]]); edges: (source, target[, relation[, label]])."""
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
                }
                for e in edges
            ],
        }
    )


# --- DOT generation -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "quoted"),
    [
        ("plain", '"plain"'),
        ('say "hi"', '"say \\"hi\\""'),
        ("\\N and \\n", '"\\\\N and \\\\n"'),
        ("multi\nline  label", '"multi line label"'),
    ],
)
def test_quote(raw: str, quoted: str) -> None:
    assert quote(raw) == quoted


def test_spec_example_dot() -> None:
    dot = to_dot(spec_example())

    assert 'n1 [label="Input Image", shape=box, style="rounded,filled"' in dot
    assert 'n4 [label="Feature Fusion", shape=hexagon' in dot
    assert [line.strip() for line in dot.splitlines() if "->" in line] == [
        "n1 -> n2;",
        "n1 -> n3;",
        "n2 -> n4;",
        "n3 -> n4;",
        "n4 -> n5;",
    ]


def test_groups_become_nested_clusters_with_anchored_edges() -> None:
    dot = to_dot(
        diagram(
            [
                ("blk", "Block", "group"),
                ("inner", "Inner", "group", "blk"),
                ("conv", "Conv", "module", "inner"),
                ("head", "Head", "output"),
                ("empty", "Empty", "group"),
            ],
            [("conv", "head"), ("blk", "head", "flows_to", "skip")],
        )
    )

    assert "subgraph cluster_n1 {" in dot
    assert "subgraph cluster_n2 {" in dot
    assert dot.index("subgraph cluster_n2") > dot.index("subgraph cluster_n1")
    assert "n1 [shape=point, style=invis" in dot  # anchor inside the cluster
    assert 'n1 -> n4 [label="skip", ltail=cluster_n1];' in dot
    assert 'n5 [label="Empty", shape=box, style="dashed"];' in dot  # no members: plain node


def test_edge_text_and_styles() -> None:
    dot = to_dot(
        diagram(
            [("d", "x > 0?", "decision"), ("a", "A"), ("b", "B")],
            [("d", "a", "branches_to", "Yes"), ("a", "b", "depends_on"), ("b", "a", "composes")],
        )
    )

    assert "shape=diamond" in dot
    assert 'n1 -> n2 [label="Yes"];' in dot
    assert 'n2 -> n3 [label="depends on", style=dashed];' in dot
    assert 'n3 -> n2 [label="composes"];' in dot


# --- rendering ------------------------------------------------------------------------


@needs_graphviz
@pytest.mark.parametrize(
    ("fmt", "magic"), [("svg", b"<?xml"), ("png", b"\x89PNG\r\n\x1a\n"), ("pdf", b"%PDF")]
)
def test_render_formats(fmt: str, magic: bytes) -> None:
    assert render(spec_example(), fmt).startswith(magic)


@needs_graphviz
def test_adversarial_labels_render_literally() -> None:
    labels = ['say "hi"', "\\N name", "\\G graph", "<b>html</b>", "{a|b}", "ümlaut ✓ 中文"]
    graph = diagram([(f"x{i}", label) for i, label in enumerate(labels)])

    svg = render(graph, "svg").decode()

    texts = {html.unescape(t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)}
    assert set(labels) <= texts
    assert "<script" not in svg


def test_missing_graphviz_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(graphviz.shutil, "which", lambda _: None)

    with pytest.raises(RenderUnavailable, match="Graphviz is not installed"):
        render(spec_example(), "svg")


def test_oversized_graph_is_not_rendered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(graphviz, "MAX_RENDER_NODES", 3)

    with pytest.raises(RenderError, match="over 3 nodes"):
        render(spec_example(), "svg")
