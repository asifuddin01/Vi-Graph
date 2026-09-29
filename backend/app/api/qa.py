"""POST /api/qa and GET /api/analyses/{diagram_id}/qa (spec §28, §12).

Questions are answered against the analysis's latest saved edit (or, without edits, the
model's reconstruction), so corrections made in the editor improve the answers. Every
question is logged with its routing decision.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.analyze import find_analysis
from app.api.deps import ImageStoreDep, RunStoreDep, SettingsDep, VLMDep, enforce_qa_rate_limit
from app.qa.answers import Grounding
from app.qa.engine import AnswerSource, answer_question
from app.qa.router import Category, route_question
from app.storage.runs import QALogEntry
from app.utils.images import ImageError, preprocess_image
from app.vlm.base import ModelInfo

router = APIRouter(prefix="/api", tags=["qa"])


class QARequest(BaseModel):
    diagram_id: str
    question: Annotated[str, Field(min_length=1, max_length=500)]


class RouteView(BaseModel):
    category: Category
    intent: str
    needs_image: bool


class QAResponse(BaseModel):
    id: str
    diagram_id: str
    question: str
    answer: str
    source: AnswerSource  # where the answer came from: graph, vlm, graph+vlm, none
    route: RouteView
    grounding: Grounding
    graph_version: int | None  # the saved edit answered from; None = original graph
    model: ModelInfo | None  # the VLM, when one was consulted
    created_at: datetime


@router.post("/qa", response_model=QAResponse, dependencies=[Depends(enforce_qa_rate_limit)])
def ask(
    body: QARequest,
    settings: SettingsDep,
    vlm: VLMDep,
    runs: RunStoreDep,
    images: ImageStoreDep,
) -> QAResponse:
    record = find_analysis(runs, body.diagram_id)
    question = " ".join(body.question.split())
    edited = runs.latest_graph_version(record.id)
    diagram = edited.graph if edited else record.graph

    # Load and preprocess the image only when this question can use it.
    image = None
    if route_question(question).needs_image or diagram is None:
        data = images.load(record.image.sha256, record.image.format)
        if data is not None:
            try:
                image = preprocess_image(
                    data, max_side=settings.image_max_side, max_pixels=settings.image_max_pixels
                ).image
            except ImageError:
                image = None

    usable_vlm = vlm if vlm.info.backend != "mock" else None
    result = answer_question(
        question,
        diagram,
        vlm=usable_vlm,
        image=image,
        vlm_unavailable_reason="the server is running the mock VLM, which can't look at images",
    )
    return _to_response(runs.log_qa(record.id, result, edited.version if edited else None))


@router.get("/analyses/{diagram_id}/qa", response_model=list[QAResponse])
def history(diagram_id: str, runs: RunStoreDep) -> list[QAResponse]:
    record = find_analysis(runs, diagram_id)
    return [_to_response(entry) for entry in runs.qa_history(record.id)]


def _to_response(entry: QALogEntry) -> QAResponse:
    result = entry.result
    return QAResponse(
        id=entry.id,
        diagram_id=entry.analysis_id,
        question=result.question,
        answer=result.answer,
        source=result.source,
        route=RouteView(
            category=result.route.category,
            intent=result.route.intent,
            needs_image=result.route.needs_image,
        ),
        grounding=result.grounding,
        graph_version=entry.graph_version,
        model=result.vlm.model if result.vlm else None,
        created_at=entry.created_at,
    )
