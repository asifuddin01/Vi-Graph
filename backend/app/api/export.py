"""POST /api/export (spec §28): json, mermaid, svg, png, pdf.

Exports either a stored analysis (its latest saved edit by default, or the model's
original reconstruction) or a graph posted in the request, which lets the editor export
exactly what is on screen. Filenames are generated, never taken from user input (§29).
"""

from __future__ import annotations

import json
from typing import Any, Literal, Self

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, model_validator

from app.api.analyze import find_analysis
from app.api.deps import RunStoreDep
from app.exporters.graphviz import RenderError, RenderUnavailable, render
from app.exporters.mermaid import to_mermaid
from app.pipeline.validation import validate_graph
from app.schemas import DiagramGraph

router = APIRouter(prefix="/api", tags=["export"])

ExportFormat = Literal["json", "mermaid", "svg", "png", "pdf"]

_MEDIA = {
    "json": ("application/json", "json"),
    "mermaid": ("text/plain; charset=utf-8", "mmd"),
    "svg": ("image/svg+xml", "svg"),
    "png": ("image/png", "png"),
    "pdf": ("application/pdf", "pdf"),
}


class ExportRequest(BaseModel):
    format: ExportFormat
    diagram_id: str | None = None
    # With diagram_id: "latest" = the latest saved edit, else the model's reconstruction.
    source: Literal["latest", "original"] = "latest"
    graph: dict[str, Any] | None = None  # alternatively, export this graph directly

    @model_validator(mode="after")
    def _one_graph_source(self) -> Self:
        if (self.diagram_id is None) == (self.graph is None):
            raise ValueError("provide exactly one of diagram_id or graph")
        return self


@router.post("/export")
def export(body: ExportRequest, runs: RunStoreDep) -> Response:
    graph, stem = _resolve(body, runs)
    media_type, extension = _MEDIA[body.format]

    if body.format == "json":
        content: bytes | str = json.dumps(graph.model_dump(mode="json"), indent=2) + "\n"
    elif body.format == "mermaid":
        content = to_mermaid(graph)
    else:
        try:
            content = render(graph, body.format)
        except RenderUnavailable as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except RenderError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="vigraph-{stem}.{extension}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


def _resolve(body: ExportRequest, runs: RunStoreDep) -> tuple[DiagramGraph, str]:
    if body.graph is not None:
        graph, problems = validate_graph(body.graph)
        if graph is None:
            raise HTTPException(status_code=422, detail=problems)
        return graph, "graph"

    record = find_analysis(runs, body.diagram_id or "")
    short_id = record.id[:8]
    if body.source == "latest":
        edited = runs.latest_graph_version(record.id)
        if edited is not None:
            return edited.graph, f"{short_id}-v{edited.version}"
    if record.graph is None:
        raise HTTPException(status_code=404, detail="this analysis has no graph to export")
    return record.graph, f"{short_id}-original" if body.source == "original" else short_id
