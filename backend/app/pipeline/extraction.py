"""Stage C orchestration (spec §8): first attempt → one corrective retry → programmatic repair.

Every outcome is recorded in the returned ``ExtractionResult`` — each attempt's raw output
and problems, every repair fix, or the reason for failure. A failure is returned as such,
never as an empty graph. ``status`` separates first-attempt validity from validity after
retry/repair, the two JSON validity rates of §20.2.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from PIL.Image import Image
from pydantic import BaseModel

from app.pipeline.json_extract import ExtractionMethod, JSONExtractionError, extract_json_object
from app.pipeline.repair import RepairError, RepairFix, repair_graph
from app.pipeline.validation import format_problem_list, validate_graph
from app.schemas import DiagramGraph
from app.vlm.base import DecodingParams, Message, VLMBackend, VLMOutput
from app.vlm.prompts import (
    GRAPH_CORRECTION,
    GRAPH_EXTRACTION,
    PromptTemplate,
    build_extraction_messages,
)

logger = logging.getLogger(__name__)

ExtractionStatus = Literal["valid_first_attempt", "valid_after_retry", "repaired", "failed"]


class Attempt(BaseModel):
    number: int
    output: VLMOutput
    json_method: ExtractionMethod | None  # None: no JSON object could be extracted
    valid: bool
    problems: list[str]  # empty when valid


class ExtractionResult(BaseModel):
    status: ExtractionStatus
    graph: DiagramGraph | None
    attempts: list[Attempt]
    repairs: list[RepairFix] = []
    repaired_from_attempt: int | None = None
    failure_reason: str | None = None
    prompt_id: str
    prompt_sha256: str
    correction_prompt_id: str
    correction_prompt_sha256: str

    @property
    def repaired(self) -> bool:
        return self.status == "repaired"


@dataclass
class _Evaluation:
    graph: DiagramGraph | None
    value: dict[str, Any] | None  # the extracted JSON object, if any
    method: ExtractionMethod | None
    problems: list[str]


def extract_graph(
    vlm: VLMBackend,
    images: Sequence[Image],
    params: DecodingParams | None = None,
    *,
    prompt: PromptTemplate = GRAPH_EXTRACTION,
    correction: PromptTemplate = GRAPH_CORRECTION,
) -> ExtractionResult:
    params = params or DecodingParams()
    prompts = {
        "prompt_id": prompt.id,
        "prompt_sha256": prompt.sha256,
        "correction_prompt_id": correction.id,
        "correction_prompt_sha256": correction.sha256,
    }
    messages = build_extraction_messages(images, prompt)

    first_output = vlm.generate(messages, params)
    first = _evaluate(first_output)
    attempts = [_attempt(1, first_output, first)]
    if first.graph is not None:
        return _finish(
            ExtractionResult(
                status="valid_first_attempt", graph=first.graph, attempts=attempts, **prompts
            )
        )

    retry_messages = [
        *messages,
        Message(role="assistant", text=first_output.text),
        Message(role="user", text=correction.render(problems=format_problem_list(first.problems))),
    ]
    second_output = vlm.generate(retry_messages, params)
    second = _evaluate(second_output)
    attempts.append(_attempt(2, second_output, second))
    if second.graph is not None:
        return _finish(
            ExtractionResult(
                status="valid_after_retry", graph=second.graph, attempts=attempts, **prompts
            )
        )

    reasons: list[str] = []
    for number, evaluation in ((2, second), (1, first)):
        if evaluation.value is None:
            continue
        try:
            repaired, fixes = repair_graph(evaluation.value)
        except RepairError as exc:
            reasons.append(f"attempt {number} could not be repaired: {exc}")
            continue
        graph, problems = validate_graph(repaired)
        if graph is not None:
            return _finish(
                ExtractionResult(
                    status="repaired",
                    graph=graph,
                    attempts=attempts,
                    repairs=fixes,
                    repaired_from_attempt=number,
                    **prompts,
                )
            )
        reasons.append(f"attempt {number} was still invalid after repair: {problems[0]}")

    if not reasons:
        reasons.append("no attempt contained a JSON object")
    return _finish(
        ExtractionResult(
            status="failed",
            graph=None,
            attempts=attempts,
            failure_reason="; ".join(reasons),
            **prompts,
        )
    )


def _evaluate(output: VLMOutput) -> _Evaluation:
    try:
        value, method = extract_json_object(output.text)
    except JSONExtractionError as exc:
        value, method, graph, problems = None, None, None, [str(exc)]
    else:
        graph, problems = validate_graph(value)
    if graph is None and output.finish_reason == "length":
        problems.insert(
            0,
            f"the response was cut off at the {output.params.max_new_tokens}-token limit; "
            "return a more compact JSON (no indentation, short ids)",
        )
    return _Evaluation(graph=graph, value=value, method=method, problems=problems)


def _attempt(number: int, output: VLMOutput, evaluation: _Evaluation) -> Attempt:
    return Attempt(
        number=number,
        output=output,
        json_method=evaluation.method,
        valid=evaluation.graph is not None,
        problems=evaluation.problems,
    )


def _finish(result: ExtractionResult) -> ExtractionResult:
    if result.status == "failed":
        logger.warning("graph extraction failed: %s", result.failure_reason)
    else:
        logger.info(
            "graph extraction %s (attempts=%d, repairs=%d)",
            result.status,
            len(result.attempts),
            len(result.repairs),
        )
    return result
