import json
from collections.abc import Sequence

import pytest
from PIL import Image

from app.pipeline.extraction import extract_graph
from app.pipeline.repair import RepairCode
from app.pipeline.validation import format_problem_list
from app.vlm import DecodingParams, Message, MockVLM
from app.vlm.base import Completion, ModelInfo, VLMBackend
from app.vlm.mock import DEFAULT_RESPONSE
from app.vlm.prompts import GRAPH_CORRECTION, GRAPH_EXTRACTION

VALID = DEFAULT_RESPONSE
PROSE = "I can see a diagram with several boxes and arrows."


def dangling(target: str = "n9") -> str:
    """Parseable JSON with one edge to a node that does not exist (repairable)."""
    data = json.loads(VALID)
    data["edges"].append({"source": "n5", "target": target, "relation": "flows_to"})
    return json.dumps(data)


def image() -> Image.Image:
    return Image.new("RGB", (64, 64), "white")


def test_valid_first_attempt() -> None:
    vlm = MockVLM([VALID])

    result = extract_graph(vlm, [image()])

    assert result.status == "valid_first_attempt"
    assert result.graph is not None and len(result.graph.nodes) == 5
    assert [(a.number, a.valid, a.json_method) for a in result.attempts] == [(1, True, "direct")]
    assert result.attempts[0].problems == []
    assert (result.repairs, result.failure_reason, result.repaired) == ([], None, False)
    assert vlm.call_count == 1


def test_prompt_identity_is_recorded() -> None:
    result = extract_graph(MockVLM(), [image()])

    assert (result.prompt_id, result.prompt_sha256) == (
        GRAPH_EXTRACTION.id,
        GRAPH_EXTRACTION.sha256,
    )
    assert result.correction_prompt_id == GRAPH_CORRECTION.id
    assert result.correction_prompt_sha256 == GRAPH_CORRECTION.sha256


def test_fenced_json_still_counts_as_first_attempt_valid() -> None:
    result = extract_graph(MockVLM([f"```json\n{VALID}\n```"]), [image()])

    assert result.status == "valid_first_attempt"
    assert result.attempts[0].json_method == "fenced"


def test_invalid_then_valid_is_valid_after_retry() -> None:
    vlm = MockVLM([dangling(), VALID])

    result = extract_graph(vlm, [image()])

    assert result.status == "valid_after_retry"
    assert [a.valid for a in result.attempts] == [False, True]
    assert result.attempts[0].problems == [
        "edge #5 'n5->n9' references node id 'n9', which does not exist"
    ]
    assert vlm.call_count == 2


def test_retry_is_a_follow_up_turn_listing_the_problems() -> None:
    vlm = MockVLM([dangling(), VALID])

    result = extract_graph(vlm, [image()])

    retry = vlm.calls[1]
    assert [m.role for m in retry] == ["user", "assistant", "user"]
    assert retry[0].text == GRAPH_EXTRACTION.text and len(retry[0].images) == 1
    assert retry[1].text == dangling()
    assert retry[2].text == GRAPH_CORRECTION.render(
        problems=format_problem_list(result.attempts[0].problems)
    )
    assert "- edge #5 'n5->n9' references node id 'n9'" in retry[2].text


def test_retry_uses_the_same_decoding_params() -> None:
    params = DecodingParams(temperature=0.3, seed=5)

    result = extract_graph(MockVLM([PROSE, VALID]), [image()], params)

    assert [a.output.params for a in result.attempts] == [params, params]


def test_repair_after_two_failures_uses_the_second_attempt() -> None:
    result = extract_graph(MockVLM([dangling("n8"), dangling("n9")]), [image()])

    assert result.status == "repaired" and result.repaired
    assert result.repaired_from_attempt == 2
    assert [fix.code for fix in result.repairs] == [RepairCode.DROPPED_EDGE]
    assert "'n9'" in result.repairs[0].message
    assert len(result.graph.edges) == 5


def test_repair_falls_back_to_the_first_attempt_when_the_retry_is_not_json() -> None:
    result = extract_graph(MockVLM([dangling(), PROSE]), [image()])

    assert result.status == "repaired"
    assert result.repaired_from_attempt == 1
    assert result.attempts[1].json_method is None


def test_failure_when_no_attempt_contains_json() -> None:
    result = extract_graph(MockVLM([PROSE]), [image()])

    assert result.status == "failed"
    assert result.graph is None
    assert result.failure_reason == "no attempt contained a JSON object"
    assert [a.valid for a in result.attempts] == [False, False]
    assert all(a.problems for a in result.attempts)


def test_failure_when_repair_cannot_salvage_anything() -> None:
    empty = json.dumps({"schema_version": "2.0", "diagram_type": "uml", "nodes": [], "edges": []})

    result = extract_graph(MockVLM([empty]), [image()])

    assert result.status == "failed"
    assert result.failure_reason == (
        "attempt 2 could not be repaired: no valid nodes remain; "
        "attempt 1 could not be repaired: no valid nodes remain"
    )


class TruncatingVLM(VLMBackend):
    """Always stops at the token limit, mid-JSON."""

    def __init__(self) -> None:
        self.calls: list[list[Message]] = []

    @property
    def info(self) -> ModelInfo:
        return ModelInfo(backend="test", model_id="truncating")

    def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion:
        self.calls.append(list(messages))
        return Completion(text=VALID[:80], finish_reason="length")


def test_truncation_is_reported_first_and_passed_to_the_retry() -> None:
    vlm = TruncatingVLM()

    result = extract_graph(vlm, [image()], DecodingParams(max_new_tokens=256))

    assert result.status == "failed"
    assert (
        result.attempts[0].problems[0].startswith("the response was cut off at the 256-token limit")
    )
    assert "cut off at the 256-token limit" in vlm.calls[1][-1].text


def test_result_serializes_for_logging() -> None:
    result = extract_graph(MockVLM([dangling("a"), dangling("b")]), [image()])

    dumped = json.loads(result.model_dump_json())

    assert dumped["status"] == "repaired"
    assert dumped["attempts"][0]["output"]["text"] == dangling("a")
    assert dumped["repairs"][0]["code"] == "dropped_edge"


def test_extraction_requires_an_image() -> None:
    with pytest.raises(ValueError, match="at least one image"):
        extract_graph(MockVLM(), [])
