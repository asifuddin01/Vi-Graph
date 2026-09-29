"""Pull a JSON object out of raw model text (spec §8 Stage C).

Models often wrap JSON in a markdown fence or add a sentence around it. Extraction tries,
in order: the whole text, fenced blocks, then the first decodable object embedded in the
text. The method used is recorded, so a stricter "bare JSON only" validity rate can still
be computed.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

ExtractionMethod = Literal["direct", "fenced", "embedded"]

_FENCE = re.compile(r"```[A-Za-z]*[ \t]*\r?\n?(.*?)```", re.DOTALL)
_MAX_EMBEDDED_CANDIDATES = 32


class JSONExtractionError(ValueError):
    """No JSON object could be extracted; the message is suitable for a retry prompt."""


def extract_json_object(text: str) -> tuple[dict[str, Any], ExtractionMethod]:
    stripped = text.strip().lstrip("﻿")
    if not stripped:
        raise JSONExtractionError("the response was empty")

    try:
        return _require_object(json.loads(stripped)), "direct"
    except json.JSONDecodeError as exc:
        direct_error = exc

    for match in _FENCE.finditer(stripped):
        try:
            value = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value, "fenced"

    decoder = json.JSONDecoder()
    starts = [i for i, char in enumerate(stripped) if char == "{"][:_MAX_EMBEDDED_CANDIDATES]
    for start in starts:
        try:
            value, _ = decoder.raw_decode(stripped, start)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value, "embedded"

    raise JSONExtractionError(
        f"the response is not valid JSON ({direct_error.msg} at line {direct_error.lineno}, "
        f"column {direct_error.colno})"
    )


def _require_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise JSONExtractionError(
            f"the top-level JSON value must be an object, not {type(value).__name__}"
        )
    return value
