import io
import random

import pytest
from PIL import Image

from app.exporters.graphviz import graphviz_available
from app.schemas import DiagramGraph
from data.generator.graphs import generate_graph
from data.generator.render import (
    CLUSTER_LAYOUTS,
    LAYOUTS,
    THEMES,
    graphviz_version,
    render,
    sample_params,
    to_styled_dot,
)

needs_graphviz = pytest.mark.skipif(not graphviz_available(), reason="Graphviz not installed")


def graph(nodes: list[tuple], edges: list[tuple] = ()) -> DiagramGraph:
    """nodes: (id, label, type[, group_id]); edges: (source, target, relation[, label])."""
    return DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": "flowchart",
            "nodes": [
                {"id": n[0], "label": n[1], "type": n[2], "group_id": n[3] if len(n) > 3 else None}
                for n in nodes
            ],
            "edges": [
                {
                    "source": e[0],
                    "target": e[1],
                    "relation": e[2],
                    "label": e[3] if len(e) > 3 else None,
                }
                for e in edges
            ],
        }
    )


GROUPED = graph(
    [("g", "Block", "group"), ("a", "A", "module", "g"), ("b", "B", "module")],
    [("a", "b", "flows_to")],
)
LABELED = graph(
    [("d", "Ok?", "decision"), ("y", "Y", "module"), ("n", "N", "module")],
    [("d", "y", "flows_to", "Yes"), ("d", "n", "flows_to", "No")],
)


def test_graphs_with_groups_only_get_cluster_layouts() -> None:
    for seed in range(50):
        params = sample_params(random.Random(seed), GROUPED, 2, LAYOUTS, list(THEMES))
        assert params.layout in CLUSTER_LAYOUTS


def test_no_cluster_layout_available_is_an_error() -> None:
    with pytest.raises(ValueError, match="can draw groups"):
        sample_params(random.Random(0), GROUPED, 2, ["radial", "circular"], ["classic"])


def test_edge_labels_never_get_orthogonal_routing() -> None:
    for seed in range(80):
        params = sample_params(random.Random(seed), LABELED, 2, ["layered_tb"], ["classic"])
        assert params.splines != "ortho"


def test_font_size_shrinks_with_level() -> None:
    def sizes(level: int) -> list[float]:
        return [
            sample_params(random.Random(s), LABELED, level, ["layered_tb"], ["classic"]).font_size
            for s in range(30)
        ]

    assert min(sizes(1)) > max(sizes(4))


def test_params_are_deterministic_per_seed() -> None:
    first = sample_params(random.Random(3), LABELED, 3, LAYOUTS, list(THEMES))
    second = sample_params(random.Random(3), LABELED, 3, LAYOUTS, list(THEMES))

    assert first == second


def test_dot_draws_groups_as_clusters_and_escapes_labels() -> None:
    tricky = graph(
        [("g", 'Say "hi"', "group"), ("a", "C:\\temp \\N", "module", "g"), ("b", "B", "module")],
        [("a", "b", "flows_to", 'x "y"')],
    )
    params = sample_params(random.Random(0), tricky, 2, ["layered_tb"], ["pastel"])

    dot = to_styled_dot(tricky, params)

    assert 'subgraph "cluster_g" {' in dot
    assert 'label="Say \\"hi\\""' in dot
    assert 'label="C:\\\\temp \\\\N"' in dot
    assert 'label="x \\"y\\""' in dot


@pytest.mark.parametrize(
    ("relation", "notation"),
    [
        ("inherits_from", "arrowhead=empty"),
        ("composes", "arrowtail=diamond"),
        ("aggregates", "arrowtail=odiamond"),
        ("depends_on", "style=dashed"),
    ],
)
def test_uml_relations_get_uml_notation(relation: str, notation: str) -> None:
    uml = graph([("a", "A", "module"), ("b", "B", "module")], [("a", "b", relation)])
    params = sample_params(random.Random(0), uml, 2, ["layered_tb"], ["classic"])

    assert notation in to_styled_dot(uml, params)


def test_decisions_are_always_diamonds() -> None:
    for seed in range(20):
        params = sample_params(random.Random(seed), LABELED, 2, LAYOUTS, list(THEMES))
        assert params.shapes["decision"] == "diamond"


@needs_graphviz
@pytest.mark.parametrize("layout", LAYOUTS)
def test_every_layout_renders(layout: str) -> None:
    sample = generate_graph(random.Random(1), 2, "neural_network")
    while sample.spec.n_groups and layout not in CLUSTER_LAYOUTS:
        sample = generate_graph(random.Random(sample.spec.n_nodes + 100), 2, "neural_network")
    params = sample_params(random.Random(2), sample.graph, 2, [layout], ["pastel"])

    image = render(sample.graph, params)

    with Image.open(io.BytesIO(image.png)) as decoded:
        assert decoded.format == "PNG"
        assert decoded.size == (image.width, image.height)
    assert image.width > 50 and image.height > 50


@needs_graphviz
@pytest.mark.parametrize("theme", list(THEMES))
def test_every_theme_renders(theme: str) -> None:
    sample = generate_graph(random.Random(5), 3, "flowchart")
    params = sample_params(random.Random(5), sample.graph, 3, ["layered_tb"], [theme])

    assert render(sample.graph, params).png.startswith(b"\x89PNG")


@needs_graphviz
def test_graphviz_version_is_reported() -> None:
    assert "graphviz version" in graphviz_version()
