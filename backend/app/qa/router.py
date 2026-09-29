"""Rule-based question router (spec §12.1).

Classifies a question into a category and a concrete intent:

- direct / structural / comparative / explanation → answered purely from the graph;
- visual → needs the image, so the VLM answers (the graph encodes no appearance);
- mixed → e.g. "why does X connect to Y?": the topological part comes from the graph,
  the reason (which the graph doesn't encode) from the image.

Rules are regular expressions checked in order; the first match wins, so more specific
patterns come first. An unmatched question is routed as ``unknown``. The spec allows this
simple router for the MVP (an LLM classifier is a possible later upgrade).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

Category = Literal[
    "direct", "structural", "comparative", "explanation", "visual", "mixed", "unknown"
]


class Route(BaseModel):
    category: Category
    intent: str
    rule: str  # the pattern that matched, for debugging (§28: routing decision logged)

    @property
    def needs_image(self) -> bool:
        return self.category in {"visual", "mixed"}


_RULES: list[tuple[Category, str, str]] = [
    # Appearance: the graph can't answer these.
    (
        "visual",
        "describe_visual",
        r"\b(colou?rs?|colou?red|shaded|shapes?|shaped|fonts?|handwrit\w*|looks? like|style[sd]?"
        r"|drawn|icons?|bold|italic|highlighted|positioned|located|location"
        r"|(left|right|top|bottom)[- ](side|corner|half)|legible|blurry|resolution)\b",
    ),
    # Reasons: the graph encodes that X connects to Y, not why.
    ("mixed", "why", r"\bwhy\b|\breasons?\b|\bpurpose\b|\bmotivat\w*"),
    (
        "explanation",
        "topology_summary",
        r"\btopolog\w*|\bstructure of (the|this) (graph|diagram)\b",
    ),
    (
        "explanation",
        "explain_merge",
        r"\b(explain|describe)\b.*\b(merg\w*|join\w*|combin\w*|meet)\b",
    ),
    (
        "explanation",
        "explain_flow",
        r"\b(explain|describe|walk (me )?through|overview|summari[sz]e)\b"
        r"|\bwhat does (this|the) (diagram|figure|graph|image) (show|do|represent)\b",
    ),
    (
        "comparative",
        "deeper_branch",
        r"\b(deep(er|est)?|long(er|est)|short(er|est))\b.*\bbranch\w*|\bbranch\w*\b.*\b(deep|long|short)",
    ),
    ("comparative", "longest_path", r"\blongest path\b|\bhow deep\b|\bdepth\b"),
    (
        "comparative",
        "common_successor",
        r"\b(receiv\w*|combin\w*|merg\w*|join\w*|meet)\b.*\bboth\b|\bboth branches\b"
        r"|\bwhere do .*\b(branches|paths)\b.*\b(merge|meet|join|combine)",
    ),
    (
        "structural",
        "fan_out",
        r"\bmultiple outgoing\b|\bmore than one (outgoing|output|successor)\b|\bfan[- ]?out\b"
        r"|\bsplits?\b|\bbranch(es)? out\b",
    ),
    (
        "structural",
        "fan_in",
        r"\bmultiple (incoming|inputs)\b|\bmore than one (incoming|input|predecessor)\b"
        r"|\bfan[- ]?in\b|\bmerg(e|es|ed|ing)\b|\bjoin(s|ed)?\b|\bcombin(e|es|ed)\b",
    ),
    (
        "structural",
        "parallel",
        r"\bparallel\b|\bconcurrent\w*|\bsimultaneous\w*|\bat the same time\b|\bbranch(es)?\b",
    ),
    (
        "structural",
        "paths",
        r"\bpaths?\b|\broutes?\b|\bhow does .+\b(reach|get to|lead to|flow to)\b|\bfrom .+ to .+",
    ),
    (
        "structural",
        "group_members",
        r"\binside\b|\bcontain(s|ed)?\b|\bmembers? of\b|\bwithin\b|\bpart of\b|\bnested\b",
    ),
    ("structural", "cycles", r"\bcycles?\b|\bcyclic\b|\bloops?\b|\bfeedback\b|\brecurren\w*"),
    (
        "direct",
        "count_edges",
        r"\bhow many\b.*\b(edges?|connections?|arrows?|links?)\b"
        r"|\bnumber of (edges|connections|arrows|links)\b",
    ),
    (
        "structural",
        "neighbors",
        r"\bconnect(ed|s|ion|ions)?\b|\bneighbou?rs?\b|\blinked\b|\badjacent\b|\bwired\b",
    ),
    ("direct", "count_nodes", r"\bhow many\b|\bnumber of\b|\bcount\b"),
    # "inputs of the diagram" is about the whole diagram, not one node's predecessors.
    (
        "direct",
        "sources",
        r"\binputs? (of|to|for) (the|this) (diagram|graph|figure|model|pipeline|network|system"
        r"|workflow|flowchart|architecture)\b",
    ),
    (
        "direct",
        "predecessors",
        r"\b(before|precede\w*|prior to|feeds? into|goes? into|comes? into|inputs? (to|of|for)"
        r"|receives?|depends? on|upstream)\b",
    ),
    (
        "direct",
        "successors",
        r"\b(after|follows?|following|next|goes? to|leads? to|feeds?|downstream|then)\b",
    ),
    ("direct", "sources", r"\b(inputs?|start\w*|begin\w*|entry|first|origin)\b"),
    ("direct", "sinks", r"\b(outputs?|final|end\w*|results?|last|terminal|produce[sd]?)\b"),
]

_COMPILED = [(category, intent, re.compile(pattern)) for category, intent, pattern in _RULES]


def route_question(question: str) -> Route:
    text = " ".join(question.casefold().split())
    for category, intent, pattern in _COMPILED:
        if pattern.search(text):
            return Route(category=category, intent=intent, rule=pattern.pattern[:80])
    return Route(category="unknown", intent="unknown", rule="")
