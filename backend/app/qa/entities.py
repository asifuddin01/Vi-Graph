"""Link node mentions in a question to graph nodes (for QA, spec §12).

- Exact: a node's label (NFC, whitespace-collapsed, casefolded — the same normalization as
  node matching, §20.1) appears in the question on word boundaries.
- Fuzzy: close misspellings of labels of 6+ characters (rapidfuzz ratio >= 88 against
  whole-word windows of the question, so a label never matches inside a longer word).
- Ids: a node id written as a word, e.g. "n3".
- Generic: "the input"/"the start" → the graph's sources, "the output"/"the end" → sinks —
  only when no node is named explicitly.

Overlapping mentions keep the longest span ("Transformer Encoder" over "Encoder"); nodes
sharing a label are all returned for that span. Mentions come back in question order,
which matters for "paths from A to B".
"""

from __future__ import annotations

import re

import networkx as nx
from pydantic import BaseModel
from rapidfuzz import fuzz

from app.graph import find_sinks, find_sources
from app.pipeline.normalize import normalize_text
from app.schemas import DiagramGraph, NodeType

FUZZY_THRESHOLD = 88.0
MIN_FUZZY_LENGTH = 6

_WORD = re.compile(r"[^\W_]+")
_GENERIC_SOURCES = re.compile(r"\bthe (input|start|beginning|entry( point)?|source)\b")
_GENERIC_SINKS = re.compile(r"\bthe (final )?(output|end|result|sink)\b")


class Mention(BaseModel):
    node_id: str
    start: int  # character span in the normalized question
    end: int
    how: str  # "exact" | "fuzzy" | "id" | "generic"


def normalize(text: str) -> str:
    return normalize_text(text).casefold()


def find_mentions(question: str, diagram: DiagramGraph, graph: nx.MultiDiGraph) -> list[Mention]:
    text = normalize(question)
    words = list(_WORD.finditer(text))
    candidates: list[Mention] = []
    for node in diagram.nodes:
        label = normalize(node.label)
        if not label:
            continue
        exact = [m.start() for m in re.finditer(re.escape(label), text) if _on_boundaries(text, m)]
        if exact:
            candidates.extend(
                Mention(node_id=node.id, start=s, end=s + len(label), how="exact") for s in exact
            )
        elif len(label) >= MIN_FUZZY_LENGTH:
            span = _fuzzy_span(label, text, words)
            if span is not None:
                candidates.append(Mention(node_id=node.id, start=span[0], end=span[1], how="fuzzy"))
        for match in re.finditer(rf"\b{re.escape(node.id.casefold())}\b", text):
            candidates.append(
                Mention(node_id=node.id, start=match.start(), end=match.end(), how="id")
            )

    mentions = _longest_non_overlapping(candidates)
    if mentions:
        return mentions

    generic: list[Mention] = []
    for pattern, finder in ((_GENERIC_SOURCES, find_sources), (_GENERIC_SINKS, find_sinks)):
        match = pattern.search(text)
        if match:
            generic.extend(
                Mention(node_id=n, start=match.start(), end=match.end(), how="generic")
                for n in finder(graph)
                if graph.nodes[n]["type"] != NodeType.GROUP.value
            )
    return sorted(generic, key=lambda m: m.start)


def unique_nodes(mentions: list[Mention]) -> list[str]:
    return list(dict.fromkeys(m.node_id for m in mentions))


def _fuzzy_span(label: str, text: str, words: list[re.Match[str]]) -> tuple[int, int] | None:
    """The best whole-word window of ``text`` resembling ``label``, if close enough."""
    size = len(_WORD.findall(label)) or 1
    best: tuple[float, int, int] | None = None
    for window in {max(1, size - 1), size, size + 1}:
        for i in range(len(words) - window + 1):
            start, end = words[i].start(), words[i + window - 1].end()
            score = fuzz.ratio(label, text[start:end])
            if score >= FUZZY_THRESHOLD and (best is None or score > best[0]):
                best = (score, start, end)
    return (best[1], best[2]) if best else None


def _on_boundaries(text: str, match: re.Match[str]) -> bool:
    before = text[match.start() - 1] if match.start() > 0 else " "
    after = text[match.end()] if match.end() < len(text) else " "
    return not before.isalnum() and not after.isalnum()


def _longest_non_overlapping(candidates: list[Mention]) -> list[Mention]:
    rank = {"exact": 0, "id": 1, "fuzzy": 2}
    ordered = sorted(candidates, key=lambda m: (-(m.end - m.start), rank[m.how], m.start))
    kept: list[Mention] = []
    for mention in ordered:
        overlaps = [k for k in kept if mention.start < k.end and k.start < mention.end]
        # Same span as a kept mention (a repeated label): keep it too; otherwise it loses.
        if not overlaps or all((k.start, k.end) == (mention.start, mention.end) for k in overlaps):
            kept.append(mention)
    unique = {(m.node_id, m.start): m for m in kept}
    return sorted(unique.values(), key=lambda m: (m.start, m.node_id))
