import hashlib

import pytest
from PIL import Image

from app.schemas import SCHEMA_VERSION, DiagramType, NodeType, Relation
from app.vlm import validate_conversation
from app.vlm.prompts import (
    GRAPH_CORRECTION,
    GRAPH_EXTRACTION,
    PROMPTS,
    build_extraction_messages,
    get_prompt,
)

# Changing a prompt's text changes its hash. If this test fails, the prompt was edited:
# bump its version and update the pinned hash here, deliberately (§18.1).
PINNED_HASHES = {
    "graph_extraction@1": "d7097c8ad971e570ebacd9fa5c62d96fe0ee3293ff4bc593e5f8021da107d409",
    "graph_correction@1": "e0f443ebad7d560db6e0a496b5431868c89b114a49177e11b2dce29e5554ae32",
}


def test_every_prompt_hash_is_pinned() -> None:
    assert {pid: prompt.sha256 for pid, prompt in PROMPTS.items()} == PINNED_HASHES


def test_hash_is_sha256_of_exact_text() -> None:
    expected = hashlib.sha256(GRAPH_EXTRACTION.text.encode("utf-8")).hexdigest()

    assert GRAPH_EXTRACTION.sha256 == expected


def test_extraction_prompt_declares_schema_version() -> None:
    assert f'schema_version "{SCHEMA_VERSION}"' in GRAPH_EXTRACTION.text


@pytest.mark.parametrize("vocabulary", [DiagramType, NodeType, Relation])
def test_extraction_prompt_lists_every_allowed_value(vocabulary: type) -> None:
    choices = "|".join(member.value for member in vocabulary)

    assert f'"{choices}"' in GRAPH_EXTRACTION.text


def test_extraction_prompt_states_schema_rules() -> None:
    text = GRAPH_EXTRACTION.text

    assert "Every node must have a non-empty label." in text
    assert 'The\n  containing node must have type "group".' in text
    assert "Return JSON only." in text


def test_extraction_prompt_has_no_placeholders() -> None:
    assert GRAPH_EXTRACTION.render() == GRAPH_EXTRACTION.text


def test_correction_prompt_renders_problems() -> None:
    text = GRAPH_CORRECTION.render(problems="- edge #1 'n3->n9' references node id 'n9'")

    assert "- edge #1 'n3->n9' references node id 'n9'" in text
    assert f'schema_version "{SCHEMA_VERSION}"' in text
    assert "$" not in text


def test_correction_prompt_requires_its_placeholder() -> None:
    with pytest.raises(KeyError, match="problems"):
        GRAPH_CORRECTION.render()


def test_get_prompt_by_id() -> None:
    assert get_prompt("graph_extraction@1") is GRAPH_EXTRACTION


def test_get_unknown_prompt_lists_known_ids() -> None:
    with pytest.raises(KeyError, match="graph_extraction@1"):
        get_prompt("graph_extraction@99")


def test_extraction_messages_are_one_user_turn_with_images() -> None:
    image = Image.new("RGB", (64, 32), "white")

    messages = build_extraction_messages([image])

    validate_conversation(messages)
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].text == GRAPH_EXTRACTION.text
    assert messages[0].images == (image,)


def test_extraction_messages_require_an_image() -> None:
    with pytest.raises(ValueError, match="at least one image"):
        build_extraction_messages([])
