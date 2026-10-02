"""Runaway guard: stop a generation that is stuck enumerating (Phase 7 finding).

On dense diagrams the model sometimes never finishes its JSON. It keeps listing invented nodes
("Shard 65", "Shard 66", … or "Linear 1024" fifty times), edges to node ids it never declared
("n84" → "n85" in a 23-node graph), or the same few edges over and over, until
max_new_tokens runs out. The guard reads the text generated so far and says when to stop.
Rules (version ``RUNAWAY_GUARD_VERSION``; parameters are the dataclass fields):

- **node loop**: at least ``min_nodes`` node labels, and the last ``node_window`` of them use
  at most ``max_templates`` label templates. A template is the casefolded,
  whitespace-collapsed label with every number replaced by ``#``, so "Shard 65" and "Shard 66"
  share one, and "Dropout 0.2" / "Conv 5x5" alternating are two;
- **undeclared edges**: each of the last ``undeclared_window`` edges has an endpoint that is
  not a declared node id;
- **edge loop**: the last ``edge_window`` edges contain at most ``edge_window // 3`` distinct
  (source, target) pairs (a diagram listed with every edge twice has ``edge_window // 2``).

Thresholds come from the synthetic-v1 train/val ground truth, not from test outputs: no 12
consecutive node labels there use fewer than 3 templates, and no diagram has more than 49
nodes. ``min_nodes`` = 50 keeps long numbered sequences in real diagrams (a ResNet's
repeated "3x3 conv, 256") from triggering the node rule.

The guard only decides when to stop: the text it leaves is exactly the prefix the model
produced. It never edits output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

RUNAWAY_GUARD_VERSION = "1"

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_JSON_STRING = r'"((?:[^"\\]|\\.)*)"'
_LABEL = re.compile(r'"label"\s*:\s*' + _JSON_STRING)
_ID = re.compile(r'"id"\s*:\s*(?:' + _JSON_STRING + r"|(-?\d+))")
_OBJECT = re.compile(r"\{[^{}]*\}")  # edge objects are flat
_SOURCE = re.compile(r'"source"\s*:\s*(?:' + _JSON_STRING + r"|(-?\d+))")
_TARGET = re.compile(r'"target"\s*:\s*(?:' + _JSON_STRING + r"|(-?\d+))")
_EDGES_KEY = '"edges"'


def label_template(label: str) -> str:
    return _NUMBER.sub("#", " ".join(label.casefold().split()))


def _value(match: re.Match[str] | None) -> str | None:
    if match is None:
        return None
    return match.group(1) if match.group(1) is not None else match.group(2)


@dataclass(frozen=True)
class RunawayGuard:
    min_nodes: int = 50
    node_window: int = 12
    max_templates: int = 2
    undeclared_window: int = 8
    edge_window: int = 12

    def check(self, text: str) -> str | None:
        """The rule that fires on this (partial) output, or None to keep generating."""
        nodes_part, _, edges_part = text.partition(_EDGES_KEY)
        labels = [m.group(1) for m in _LABEL.finditer(nodes_part)]
        if len(labels) >= max(self.min_nodes, self.node_window):
            recent = {label_template(label) for label in labels[-self.node_window :]}
            if len(recent) <= self.max_templates:
                shown = ", ".join(sorted(recent))
                return (
                    f"node loop: {len(labels)} nodes, the last {self.node_window} use "
                    f"{len(recent)} label template(s) ({shown})"
                )
        if not edges_part:
            return None

        declared = {_value(m) for m in _ID.finditer(nodes_part)}
        edges = []
        for obj in _OBJECT.finditer(edges_part):
            source = _value(_SOURCE.search(obj.group()))
            target = _value(_TARGET.search(obj.group()))
            if source is not None and target is not None:
                edges.append((source, target))

        recent_edges = edges[-self.undeclared_window :]
        if len(recent_edges) == self.undeclared_window and all(
            source not in declared or target not in declared for source, target in recent_edges
        ):
            return (
                f"undeclared edges: the last {self.undeclared_window} edges point to node ids "
                f"that were never declared ({len(declared)} declared)"
            )
        recent_edges = edges[-self.edge_window :]
        distinct = len(set(recent_edges))
        if len(recent_edges) == self.edge_window and distinct <= self.edge_window // 3:
            return f"edge loop: the last {self.edge_window} edges repeat {distinct} distinct pairs"
        return None
