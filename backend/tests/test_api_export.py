import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.exporters import graphviz
from app.exporters.graphviz import graphviz_available
from app.vlm import MockVLM
from tests.api_env import Env, make_env, png, upload

needs_graphviz = pytest.mark.skipif(not graphviz_available(), reason="Graphviz not installed")


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return make_env(tmp_path)


def export(client: TestClient, **body: object):
    return client.post("/api/export", json=body)


def analyzed(env: Env) -> dict:
    return upload(env, png()).json()


# --- text formats ---------------------------------------------------------------------


def test_json_export_of_an_analysis(env: Env) -> None:
    body = analyzed(env)

    response = export(env.client, diagram_id=body["diagram_id"], format="json")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert json.loads(response.content) == body["graph"]
    short = body["diagram_id"][:8]
    assert response.headers["content-disposition"] == f'attachment; filename="vigraph-{short}.json"'
    assert response.headers["x-content-type-options"] == "nosniff"


def test_mermaid_export(env: Env) -> None:
    body = analyzed(env)

    response = export(env.client, diagram_id=body["diagram_id"], format="mermaid")

    assert response.text == body["mermaid"]
    assert response.headers["content-disposition"].endswith('.mmd"')


def test_latest_edit_is_exported_by_default_and_original_on_request(env: Env) -> None:
    body = analyzed(env)
    edited = json.loads(json.dumps(body["graph"]))
    edited["nodes"][0]["label"] = "Edited Input"
    env.client.put(f"/api/analyses/{body['diagram_id']}/graph", json={"graph": edited})
    short = body["diagram_id"][:8]

    latest = export(env.client, diagram_id=body["diagram_id"], format="json")
    original = export(env.client, diagram_id=body["diagram_id"], format="json", source="original")

    assert json.loads(latest.content)["nodes"][0]["label"] == "Edited Input"
    assert latest.headers["content-disposition"].endswith(f'vigraph-{short}-v1.json"')
    assert json.loads(original.content)["nodes"][0]["label"] == "Input Image"
    assert original.headers["content-disposition"].endswith(f'vigraph-{short}-original.json"')


def test_a_posted_graph_is_validated_and_exported(env: Env) -> None:
    graph = analyzed(env)["graph"]

    response = export(env.client, graph=graph, format="mermaid")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="vigraph-graph.mmd"'


def test_an_invalid_posted_graph_lists_its_problems(env: Env) -> None:
    graph = analyzed(env)["graph"]
    graph["edges"].append({"source": "n1", "target": "zz", "relation": "flows_to"})

    response = export(env.client, graph=graph, format="json")

    assert response.status_code == 422
    assert response.json()["detail"] == [
        "edge #5 'n1->zz' references node id 'zz', which does not exist"
    ]


# --- request errors -------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [{"format": "json"}, {"format": "json", "diagram_id": "0" * 32, "graph": {}}],
    ids=["neither", "both"],
)
def test_exactly_one_graph_source_is_required(env: Env, body: dict) -> None:
    response = env.client.post("/api/export", json=body)

    assert response.status_code == 422
    assert "exactly one of diagram_id or graph" in response.text


def test_unknown_format_is_rejected(env: Env) -> None:
    body = analyzed(env)

    assert export(env.client, diagram_id=body["diagram_id"], format="docx").status_code == 422


def test_unknown_analysis_is_404(env: Env) -> None:
    assert export(env.client, diagram_id="0" * 32, format="json").status_code == 404


def test_failed_analysis_without_edits_has_nothing_to_export(tmp_path: Path) -> None:
    env = make_env(tmp_path, MockVLM(["no json"]))
    body = analyzed(env)

    response = export(env.client, diagram_id=body["diagram_id"], format="json")

    assert response.status_code == 404
    assert response.json()["detail"] == "this analysis has no graph to export"


# --- rendered formats -----------------------------------------------------------------


@needs_graphviz
@pytest.mark.parametrize(
    ("fmt", "media_type", "magic"),
    [
        ("svg", "image/svg+xml", b"<?xml"),
        ("png", "image/png", b"\x89PNG"),
        ("pdf", "application/pdf", b"%PDF"),
    ],
)
def test_rendered_exports(env: Env, fmt: str, media_type: str, magic: bytes) -> None:
    body = analyzed(env)

    response = export(env.client, diagram_id=body["diagram_id"], format=fmt)

    assert response.status_code == 200
    assert response.headers["content-type"] == media_type
    assert response.content.startswith(magic)


def test_rendering_without_graphviz_is_501_but_json_still_works(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(graphviz.shutil, "which", lambda _: None)
    body = analyzed(env)

    svg = export(env.client, diagram_id=body["diagram_id"], format="svg")
    as_json = export(env.client, diagram_id=body["diagram_id"], format="json")

    assert svg.status_code == 501
    assert "Graphviz is not installed" in svg.json()["detail"]
    assert as_json.status_code == 200
