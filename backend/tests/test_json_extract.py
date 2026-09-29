import pytest

from app.pipeline.json_extract import JSONExtractionError, extract_json_object

OBJECT = '{"schema_version": "2.0", "nodes": [{"id": "n1"}]}'
PARSED = {"schema_version": "2.0", "nodes": [{"id": "n1"}]}


@pytest.mark.parametrize(
    "text",
    [OBJECT, f"  \n{OBJECT}\n\n", f"﻿{OBJECT}"],
    ids=["bare", "surrounding-whitespace", "byte-order-mark"],
)
def test_bare_json_is_direct(text: str) -> None:
    assert extract_json_object(text) == (PARSED, "direct")


@pytest.mark.parametrize(
    "text",
    [
        f"```json\n{OBJECT}\n```",
        f"```\n{OBJECT}\n```",
        f"Here is the graph:\n```JSON\n{OBJECT}\n```\nLet me know if you need more.",
        f"```json {OBJECT}```",
    ],
    ids=["json-fence", "plain-fence", "fence-with-prose", "fence-on-one-line"],
)
def test_fenced_json_is_extracted(text: str) -> None:
    assert extract_json_object(text) == (PARSED, "fenced")


def test_non_object_fence_is_skipped_for_a_later_object_fence() -> None:
    text = f"```json\n[1, 2]\n```\nand\n```json\n{OBJECT}\n```"

    assert extract_json_object(text) == (PARSED, "fenced")


@pytest.mark.parametrize(
    "text",
    [
        f"Sure! {OBJECT}",
        f"The diagram is: {OBJECT} Hope this helps.",
        f"Use {{braces}} carefully. {OBJECT}",
    ],
    ids=["prefix", "prefix-and-suffix", "stray-brace-before"],
)
def test_embedded_json_is_extracted(text: str) -> None:
    assert extract_json_object(text) == (PARSED, "embedded")


@pytest.mark.parametrize("text", ["", "   \n\t"], ids=["empty", "whitespace"])
def test_empty_response_is_rejected(text: str) -> None:
    with pytest.raises(JSONExtractionError, match="empty"):
        extract_json_object(text)


def test_prose_without_json_is_rejected_with_the_parse_position() -> None:
    with pytest.raises(JSONExtractionError, match=r"not valid JSON \(Expecting value at line 1"):
        extract_json_object("I cannot see any diagram in this image.")


def test_truncated_json_is_rejected() -> None:
    with pytest.raises(JSONExtractionError, match="not valid JSON"):
        extract_json_object(OBJECT[:-10])


@pytest.mark.parametrize("text", ["[1, 2, 3]", '"just a string"', "42"])
def test_top_level_non_object_is_rejected(text: str) -> None:
    with pytest.raises(JSONExtractionError, match="must be an object"):
        extract_json_object(text)
