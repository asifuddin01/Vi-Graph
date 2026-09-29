"""Question answering over a reconstructed diagram (spec §12.1 routing procedure).

1. Route the question (``router``) and find the nodes it mentions (``entities``).
2. Direct / structural / comparative / explanation → answered from the graph alone.
3. Visual → the VLM answers from the image, with the graph as context.
4. Mixed ("why") → the graph answers the topological part; the VLM adds the reason.
   Unmatched questions also go to the VLM, with the graph as context.

When the VLM is needed but unavailable (no image, or only the mock backend, which can't
look at images), the answer says so rather than guessing.
"""

from __future__ import annotations

import logging
from typing import Literal

from PIL.Image import Image
from pydantic import BaseModel

from app.graph import build_graph
from app.qa.answers import GraphAnswer, Grounding, answer_from_graph
from app.qa.entities import find_mentions, unique_nodes
from app.qa.router import Route, route_question
from app.schemas import DiagramGraph
from app.vlm.base import DecodingParams, VLMBackend, VLMOutput
from app.vlm.prompts import VISUAL_QA, build_visual_qa_messages

logger = logging.getLogger(__name__)

AnswerSource = Literal["graph", "vlm", "graph+vlm", "none"]

QA_PARAMS = DecodingParams(max_new_tokens=256)

_HINT = (
    "Try asking what comes before or after a node, which branches run in parallel, the "
    "paths between two nodes, or ask for an explanation of the flow."
)


class QAResult(BaseModel):
    question: str
    answer: str
    route: Route
    mentioned: list[str]
    grounding: Grounding
    source: AnswerSource
    vlm: VLMOutput | None = None  # the model call, when one was made (for logging)
    prompt_id: str | None = None
    prompt_sha256: str | None = None


def answer_question(
    question: str,
    diagram: DiagramGraph | None,
    *,
    vlm: VLMBackend | None,
    image: Image | None,
    vlm_unavailable_reason: str = "no vision model is available",
) -> QAResult:
    route = route_question(question)
    graph_answer: GraphAnswer | None = None
    mentioned: list[str] = []
    if diagram is not None:
        graph = build_graph(diagram)
        mentions = find_mentions(question, diagram, graph)
        mentioned = unique_nodes(mentions)
        graph_answer = answer_from_graph(route.intent, diagram, graph, mentions)

    def result(answer: str, source: AnswerSource, **extra: object) -> QAResult:
        grounding = graph_answer.grounding if graph_answer else Grounding(nodes=mentioned)
        outcome = QAResult(
            question=question,
            answer=answer,
            route=route,
            mentioned=mentioned,
            grounding=grounding,
            source=source,
            **extra,
        )
        logger.info(
            "qa route=%s/%s source=%s mentioned=%s",
            route.category,
            route.intent,
            source,
            mentioned,
        )
        return outcome

    if graph_answer is not None and graph_answer.complete:
        return result(graph_answer.text, "graph")

    graph_part = graph_answer.text if graph_answer and graph_answer.text else ""

    if vlm is None or image is None:
        reason = (
            vlm_unavailable_reason if image is not None else "the original image is not available"
        )
        if diagram is None:
            return result(f"There is no reconstructed graph to answer from, and {reason}.", "none")
        if route.category == "unknown" and not graph_part:
            return result(f"I couldn't map that question to the graph. {_HINT}", "none")
        missing = (
            "The graph doesn't record why; answering that needs the image"
            if route.category == "mixed"
            else "Answering this needs the image"
        )
        text = f"{graph_part} {missing}, but {reason}.".strip()
        return result(text, "graph" if graph_part else "none")

    graph_json = diagram.model_dump_json() if diagram is not None else None
    output = vlm.generate(build_visual_qa_messages(image, graph_json, question), QA_PARAMS)
    vlm_text = output.text.strip() or "The model returned no answer."
    text = f"{graph_part} {vlm_text}".strip()
    return result(
        text,
        "graph+vlm" if graph_part else "vlm",
        vlm=output,
        prompt_id=VISUAL_QA.id,
        prompt_sha256=VISUAL_QA.sha256,
    )
