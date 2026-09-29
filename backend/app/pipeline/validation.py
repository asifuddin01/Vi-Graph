"""Validate extracted JSON against the schema, describing failures for the retry prompt."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.schemas import DiagramGraph, GraphStructureError

MAX_LISTED_PROBLEMS = 20
_HIDE_INPUT_FOR = {"missing", "extra_forbidden", "json_invalid"}


def validate_graph(value: dict[str, Any]) -> tuple[DiagramGraph | None, list[str]]:
    """The validated graph and no problems, or no graph and every problem found."""
    try:
        return DiagramGraph.model_validate(value), []
    except ValidationError as exc:
        return None, describe_validation_error(exc)


def describe_validation_error(exc: ValidationError) -> list[str]:
    problems: list[str] = []
    for error in exc.errors():
        cause = error.get("ctx", {}).get("error")
        if isinstance(cause, GraphStructureError):
            problems.extend(cause.problems)
            continue
        message = error["msg"].removeprefix("Value error, ")
        value = error.get("input")
        if error["type"] not in _HIDE_INPUT_FOR and _is_scalar(value):
            message += f" (got {_shorten(repr(value))})"
        location = _format_location(error["loc"])
        problems.append(f"{location}: {message}" if location else message)
    return problems


def format_problem_list(problems: list[str], limit: int = MAX_LISTED_PROBLEMS) -> str:
    lines = [f"- {problem}" for problem in problems[:limit]]
    if len(problems) > limit:
        lines.append(f"- ... and {len(problems) - limit} more")
    return "\n".join(lines)


def _format_location(loc: tuple[int | str, ...]) -> str:
    text = ""
    for part in loc:
        text += f"[{part}]" if isinstance(part, int) else (f".{part}" if text else str(part))
    return text


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _shorten(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."
