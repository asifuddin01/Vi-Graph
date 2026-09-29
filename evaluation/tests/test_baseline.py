import io
import random
import shutil
from pathlib import Path

import pytest
from PIL import Image

from app.exporters.graphviz import graphviz_available
from app.schemas import DiagramGraph
from data.generator.dataset import build_dataset, default_config
from data.generator.render import render, sample_params
from evaluation.tests.helpers import graph

cv2 = pytest.importorskip("cv2")
pytest.importorskip("pytesseract")
pytestmark = pytest.mark.skipif(
    not graphviz_available() or shutil.which("tesseract") is None,
    reason="needs Graphviz and the tesseract binary",
)

from evaluation.__main__ import main as cli  # noqa: E402
from evaluation.baseline import reconstruct  # noqa: E402
from evaluation.metrics.scores import score_sample  # noqa: E402
from evaluation.results import read_run  # noqa: E402


def draw(diagram: DiagramGraph, layout: str = "layered_tb", theme: str = "classic") -> bytes:
    params = sample_params(random.Random(0), diagram, 1, [layout], [theme])
    return render(diagram, params).png


CHAIN = graph(
    [
        ("a", "Load Data", "input"),
        ("b", "Tokenize"),
        ("c", "Train Model"),
        ("d", "Report", "output"),
    ],
    [("a", "b"), ("b", "c"), ("c", "d")],
)


@pytest.mark.parametrize("theme", ["classic", "dark", "vivid"])
def test_reads_a_simple_chain_in_any_theme(theme: str) -> None:
    result = reconstruct(draw(CHAIN, theme=theme))

    scores = score_sample(result.graph, CHAIN)
    assert scores.nodes.f1 == 1.0 and scores.labels.exact == 4
    assert scores.edges.f1 == 1.0  # every arrow, in the right direction


def test_arrow_direction_comes_from_the_arrowhead_not_the_layout() -> None:
    backwards = graph([("a", "Alpha"), ("b", "Bravo")], [("b", "a")])  # drawn bottom → top

    result = reconstruct(draw(backwards))

    labels = {n.id: n.label for n in result.graph.nodes}
    assert [(labels[e.source], labels[e.target]) for e in result.graph.edges] == [
        ("Bravo", "Alpha")
    ]


def test_decisions_and_edge_labels() -> None:
    flow = graph(
        [("s", "Start", "input"), ("d", "Valid?", "decision"), ("y", "Save"), ("n", "Reject")],
        [("s", "d"), ("d", "y", "flows_to", "Yes"), ("d", "n", "flows_to", "No")],
    )

    result = reconstruct(draw(flow))

    by_label = {n.label: n for n in result.graph.nodes}
    assert by_label["Valid?"].type == "decision"
    labels = {n.id: n.label for n in result.graph.nodes}
    edge_text = {(labels[e.source], labels[e.target]): e.label for e in result.graph.edges}
    assert edge_text[("Valid?", "Reject")] == "No"
    # Attached to the right edge, though OCR clips a letter that touches the stroke ("es").
    assert edge_text[("Valid?", "Save")]


def test_groups_become_group_nodes_with_members() -> None:
    grouped = graph(
        [
            ("g", "Backbone", "group"),
            ("a", "Input", "input"),
            ("b", "Conv", "module", "g"),
            ("c", "Pool", "module", "g"),
            ("d", "Head", "output"),
        ],
        [("a", "b"), ("b", "c"), ("c", "d")],
    )

    # Filled group boxes; dashed borders don't form closed shapes (a v1 limitation). Left to
    # right, so no edge runs through the group's label (it would erase letters).
    result = reconstruct(draw(grouped, layout="layered_lr", theme="corporate"))

    nodes = {n.label: n for n in result.graph.nodes}
    assert nodes["Backbone"].type == "group"
    assert nodes["Conv"].group_id == nodes["Pool"].group_id == nodes["Backbone"].id
    assert nodes["Input"].group_id is None
    assert score_sample(result.graph, grouped).grouping.correct == 5


def test_blank_image_gives_no_graph() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (200, 120), "white").save(buffer, format="PNG")

    result = reconstruct(buffer.getvalue())

    assert result.graph is None and result.notes


def test_baseline_runs_through_the_evaluation_cli(tmp_path: Path) -> None:
    data = tmp_path / "data"
    build_dataset(default_config("tiny", seed=5, train=0, val=0, test=4), data)
    out = tmp_path / "baseline"

    assert (
        cli(["run", "--dataset", str(data), "--backend", "baseline", "--out", str(out), "--quiet"])
        == 0
    )

    run = read_run(out)
    assert run.config.predictor == "baseline:v1" and run.metadata is None
    assert run.predictor_info["baseline_version"] == "1"
    assert run.predictor_info["tesseract"].startswith("5")
    assert "baseline_version 1" in (out / "report.md").read_text()
