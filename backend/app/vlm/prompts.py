"""Versioned prompt templates (spec §8 Stage B, §18.1).

Every prompt has a name, a hand-bumped version, and the SHA-256 of its exact text. Both are
logged with every inference call. ``test_prompts.py`` pins each hash, so the text cannot
change without a deliberate version bump.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from string import Template

from PIL.Image import Image

from app.schemas import SCHEMA_VERSION, DiagramType, NodeType, Relation
from app.vlm.base import Message


@dataclass(frozen=True)
class PromptTemplate:
    """A prompt; ``$placeholders`` in ``text`` are filled by ``render``.

    The hash covers the template, placeholders included, so it identifies the wording
    independently of per-call values.
    """

    name: str
    version: str
    text: str

    @property
    def id(self) -> str:
        return f"{self.name}@{self.version}"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def render(self, **values: str) -> str:
        return Template(self.text).substitute(values)


def _choices(vocabulary: type[StrEnum]) -> str:
    return "|".join(member.value for member in vocabulary)


# Spec §8 Stage B, with the allowed values filled in from the schema enums, plus two
# requirements the schema enforces that the spec's text leaves implicit: non-empty node
# labels, and containers having type "group".
_GRAPH_EXTRACTION = Template("""\
You are a diagram understanding system.

Analyze the provided diagram and reconstruct its structure.

Return ONLY valid JSON using schema_version "$schema_version":

{
  "schema_version": "$schema_version",
  "diagram_type": "$diagram_types",
  "nodes": [
    {
      "id": "...",
      "label": "...",
      "type": "$node_types",
      "group_id": "... or null"
    }
  ],
  "edges": [
    {
      "source": "...",
      "target": "...",
      "relation": "$relations",
      "label": "... or null",
      "condition": "... or null"
    }
  ]
}

Requirements:
- Include every clearly visible component.
- Preserve exact visible labels whenever possible.
- Every node must have a non-empty label.
- Infer an edge only when the visual evidence supports it.
- Do not invent nodes that are not visible.
- Use unique node IDs.
- Every edge must reference existing node IDs.
- If a node is visually nested inside another (a box inside a box, a
  labeled cluster), set its group_id to the containing node's id. The
  containing node must have type "group".
- If an edge has a visible text label (e.g. "Yes"/"No" on a decision
  branch), populate edge.label with that exact text.
- Return JSON only.
""").substitute(
    schema_version=SCHEMA_VERSION,
    diagram_types=_choices(DiagramType),
    node_types=_choices(NodeType),
    relations=_choices(Relation),
)

GRAPH_EXTRACTION = PromptTemplate(name="graph_extraction", version="1", text=_GRAPH_EXTRACTION)

# The corrective follow-up turn of §8 Stage C. $problems is a bullet list of the specific
# validation errors in the previous answer.
_GRAPH_CORRECTION = Template("""\
Your previous response could not be accepted. Problems:
$$problems

Fix these problems and return the complete corrected JSON using schema_version \
"$schema_version". Keep everything that was already correct.
Return JSON only.
""").substitute(schema_version=SCHEMA_VERSION)

GRAPH_CORRECTION = PromptTemplate(name="graph_correction", version="1", text=_GRAPH_CORRECTION)

PROMPTS: dict[str, PromptTemplate] = {
    prompt.id: prompt for prompt in [GRAPH_EXTRACTION, GRAPH_CORRECTION]
}


def get_prompt(prompt_id: str) -> PromptTemplate:
    try:
        return PROMPTS[prompt_id]
    except KeyError:
        known = ", ".join(sorted(PROMPTS))
        raise KeyError(f"unknown prompt {prompt_id!r} (known: {known})") from None


def build_extraction_messages(
    images: Sequence[Image], prompt: PromptTemplate = GRAPH_EXTRACTION
) -> list[Message]:
    """The first-attempt conversation: one user turn with the prompt and the diagram."""
    if not images:
        raise ValueError("graph extraction needs at least one image")
    return [Message(role="user", text=prompt.text, images=tuple(images))]
