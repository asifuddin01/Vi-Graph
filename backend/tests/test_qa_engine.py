from pathlib import Path

from PIL import Image

from app.qa.engine import answer_question
from app.schemas import DiagramGraph
from app.vlm.prompts import VISUAL_QA
from tests.vlm_doubles import RecordingVLM

FIXTURES = Path(__file__).parent / "fixtures"


def spec() -> DiagramGraph:
    return DiagramGraph.model_validate_json((FIXTURES / "graph_v2_example.json").read_text())


def image() -> Image.Image:
    return Image.new("RGB", (64, 64), "white")


def test_graph_questions_never_call_the_model() -> None:
    vlm = RecordingVLM()

    result = answer_question("What comes after the CNN Encoder?", spec(), vlm=vlm, image=image())

    assert result.answer == "After CNN Encoder, the flow goes to Feature Fusion."
    assert result.source == "graph"
    assert (result.route.category, result.route.intent) == ("direct", "successors")
    assert result.mentioned == ["n2"]
    assert result.grounding.edges == [("n2", "n4")]
    assert vlm.calls == [] and result.vlm is None


def test_visual_question_is_answered_by_the_model_with_image_graph_and_question() -> None:
    vlm = RecordingVLM()

    result = answer_question("What color is the CNN Encoder?", spec(), vlm=vlm, image=image())

    assert result.answer == "The encoder boxes are drawn in blue."
    assert result.source == "vlm"
    assert result.vlm is not None and result.vlm.model.model_id == "recording-vlm"
    assert (result.prompt_id, result.prompt_sha256) == (VISUAL_QA.id, VISUAL_QA.sha256)
    [message] = vlm.calls[0]
    assert len(message.images) == 1
    assert '"label":"CNN Encoder"' in message.text
    assert message.text.endswith("Question: What color is the CNN Encoder?\n")
    assert result.grounding.nodes == ["n2"]  # the mentioned node


def test_why_combines_the_graph_part_and_the_models_reason() -> None:
    vlm = RecordingVLM("The fusion step needs features from both encoders.")

    result = answer_question(
        "Why does the Transformer Encoder connect to Feature Fusion?",
        spec(),
        vlm=vlm,
        image=image(),
    )

    assert result.answer == (
        "In the graph, Transformer Encoder connects directly to Feature Fusion (flows to). "
        "The fusion step needs features from both encoders."
    )
    assert result.source == "graph+vlm"
    assert result.grounding.edges == [("n3", "n4")]


def test_why_without_a_model_explains_what_is_missing() -> None:
    result = answer_question(
        "Why does the Transformer Encoder connect to Feature Fusion?",
        spec(),
        vlm=None,
        image=image(),
    )

    assert result.answer == (
        "In the graph, Transformer Encoder connects directly to Feature Fusion (flows to). "
        "The graph doesn't record why; answering that needs the image, but no vision model "
        "is available."
    )
    assert result.source == "graph"


def test_visual_question_without_a_model() -> None:
    result = answer_question(
        "What color is the CNN Encoder?",
        spec(),
        vlm=None,
        image=image(),
        vlm_unavailable_reason="the server is running the mock VLM",
    )

    assert (
        result.answer == "Answering this needs the image, but the server is running the mock VLM."
    )
    assert result.source == "none"


def test_missing_image_is_reported() -> None:
    result = answer_question("What color is it?", spec(), vlm=RecordingVLM(), image=None)

    assert result.answer.endswith("but the original image is not available.")


def test_unknown_question_without_a_model_gives_a_hint() -> None:
    result = answer_question("Tell me a joke", spec(), vlm=None, image=None)

    assert result.answer.startswith("I couldn't map that question to the graph. Try asking")
    assert (result.route.category, result.source) == ("unknown", "none")


def test_unknown_question_goes_to_the_model() -> None:
    vlm = RecordingVLM("It is a two-branch vision model.")

    result = answer_question("Tell me about it", spec(), vlm=vlm, image=image())

    assert (result.answer, result.source) == ("It is a two-branch vision model.", "vlm")


def test_no_graph_falls_back_to_the_image() -> None:
    vlm = RecordingVLM("Two encoders feed a classifier.")

    result = answer_question("What comes after the CNN Encoder?", None, vlm=vlm, image=image())

    assert result.source == "vlm"
    assert "(no graph could be extracted from this diagram)" in vlm.calls[0][0].text


def test_no_graph_and_no_model() -> None:
    result = answer_question("What comes after X?", None, vlm=None, image=image())

    assert result.answer == (
        "There is no reconstructed graph to answer from, and no vision model is available."
    )


def test_empty_model_reply_is_reported() -> None:
    result = answer_question("What color is it?", spec(), vlm=RecordingVLM("  "), image=image())

    assert result.answer == "The model returned no answer."
