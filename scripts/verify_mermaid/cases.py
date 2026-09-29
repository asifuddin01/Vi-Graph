"""Adversarial graphs for scripts/verify_mermaid/check.mjs; prints them as Mermaid JSON.

Run from the repo root: PYTHONPATH=backend .venv/bin/python scripts/verify_mermaid/cases.py
"""

import json

from app.exporters.mermaid import to_mermaid
from app.schemas import DiagramGraph, Relation

NASTY_LABELS = [
    'He said "hi"',
    "C# & F#",
    "a; b",
    "x | y",
    "<script>alert(1)</script>",
    "`**bold**`",
    "#quot; literal",
    "end",
    "Größe ≥ 3 → ✓",
    "[brackets] {braces} (parens)",
    "50% & 100%",
    "--> arrow",
    "subgraph",
    "click n1 call alert()",
    "%% comment",
    "A\\nB",
    "#35;",
    "C:\\path\\to",
]
NODE_TYPES = ["input", "module", "operation", "decision", "fusion", "output", "group", "unknown"]


def graph(nodes: list[tuple], edges: list[tuple]) -> DiagramGraph:
    """nodes: (id, label, type, group_id); edges: (source, target, relation, label)."""
    return DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": "flowchart",
            "nodes": [
                {"id": node_id, "label": label, "type": node_type, "group_id": group_id}
                for node_id, label, node_type, group_id in nodes
            ],
            "edges": [
                {"source": source, "target": target, "relation": relation, "label": label}
                for source, target, relation, label in edges
            ],
        }
    )


CASES = [
    (
        "nasty-node-labels",
        graph([(f"x{i}", label, "module", None) for i, label in enumerate(NASTY_LABELS)], []),
        NASTY_LABELS,
    ),
    (
        "nasty-edge-labels",
        graph(
            [("a", "A", "decision", None), ("b", "B", "module", None)],
            [("a", "b", "flows_to", label) for label in NASTY_LABELS],
        ),
        NASTY_LABELS,
    ),
    (
        "all-shapes",
        graph(
            [(t, f"{t} node", t, None) for t in NODE_TYPES],
            [("input", "module", "flows_to", None)],
        ),
        [f"{t} node" for t in NODE_TYPES],
    ),
    (
        "nested-groups-and-edge-to-group",
        graph(
            [
                ("blk", "ResNet Block", "group", None),
                ("inner", "Inner", "group", "blk"),
                ("c", "Conv", "module", "inner"),
                ("r", "ReLU", "operation", "blk"),
                ("h", "Head", "output", None),
            ],
            [
                ("c", "r", "flows_to", None),
                ("r", "h", "flows_to", None),
                ("blk", "h", "flows_to", "skip"),
            ],
        ),
        ["ResNet Block", "Inner", "Conv", "ReLU", "Head", "skip"],
    ),
    (
        "all-relations-parallel-and-self-loop",
        graph(
            [("a", "A", "module", None), ("b", "B", "module", None)],
            [("a", "b", r.value, None) for r in Relation] + [("a", "a", "flows_to", "again")],
        ),
        ["A", "B", "again", "inherits from", "depends on"],
    ),
]

if __name__ == "__main__":
    print(
        json.dumps(
            [
                {"name": name, "mermaid": to_mermaid(case), "labels": labels}
                for name, case, labels in CASES
            ]
        )
    )
