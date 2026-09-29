"""Stage D normalization of a validated graph (spec §8). Every change is recorded.

- Text: node labels, edge labels, and conditions are NFC-normalized with whitespace runs
  (incl. line breaks from multi-line labels) collapsed; an edge label/condition that ends up
  empty becomes null.
- Duplicate edges (identical in every field) are removed, keeping the first.
- Node ids are renumbered n1..nk in node order (edges and group_ids follow), giving the
  deterministic ids Mermaid generation needs (§10). ``id_map`` records old → new.
- Nodes sharing a label are flagged, never merged: repeated labels are often legitimate
  (e.g. two "Conv 3x3" layers).

Edge direction is preserved exactly: the relation vocabulary has no inverse forms (no
"flows_from"), so nothing needs flipping, and relation names are already exact after
validation (§10: preserve topology exactly).
"""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas import DiagramGraph


class NormalizationCode(StrEnum):
    NORMALIZED_TEXT = "normalized_text"
    EMPTY_TEXT_TO_NULL = "empty_text_to_null"
    REMOVED_DUPLICATE_EDGE = "removed_duplicate_edge"
    RENUMBERED_IDS = "renumbered_ids"
    FLAGGED_DUPLICATE_LABEL = "flagged_duplicate_label"  # informational; nothing changed


class NormalizationChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: NormalizationCode
    message: str


class NormalizationResult(BaseModel):
    graph: DiagramGraph
    changes: list[NormalizationChange]
    id_map: dict[str, str]  # original node id → normalized id, for every node


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def normalize_graph(graph: DiagramGraph) -> NormalizationResult:
    changes: list[NormalizationChange] = []

    def note(code: NormalizationCode, message: str) -> None:
        changes.append(NormalizationChange(code=code, message=message))

    data = graph.model_dump(mode="json")
    nodes: list[dict[str, Any]] = data["nodes"]
    edges: list[dict[str, Any]] = data["edges"]

    for node in nodes:
        label = normalize_text(node["label"])
        if label != node["label"]:
            note(
                NormalizationCode.NORMALIZED_TEXT,
                f"node {node['id']!r} label {node['label']!r} -> {label!r}",
            )
            node["label"] = label

    for index, edge in enumerate(edges):
        for field in ("label", "condition"):
            value = edge[field]
            if value is None:
                continue
            normalized = normalize_text(value)
            if not normalized:
                note(
                    NormalizationCode.EMPTY_TEXT_TO_NULL,
                    f"edge #{index} {field} {value!r} -> null",
                )
                edge[field] = None
            elif normalized != value:
                note(
                    NormalizationCode.NORMALIZED_TEXT,
                    f"edge #{index} {field} {value!r} -> {normalized!r}",
                )
                edge[field] = normalized

    unique_edges: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for index, edge in enumerate(edges):
        key = (edge["source"], edge["target"], edge["relation"], edge["label"], edge["condition"])
        if key in seen:
            note(
                NormalizationCode.REMOVED_DUPLICATE_EDGE,
                f"edge #{index} '{edge['source']}->{edge['target']}' duplicates an earlier edge",
            )
            continue
        seen.add(key)
        unique_edges.append(edge)
    data["edges"] = edges = unique_edges

    id_map = {node["id"]: f"n{position}" for position, node in enumerate(nodes, start=1)}
    renamed = sum(old != new for old, new in id_map.items())
    if renamed:
        note(
            NormalizationCode.RENUMBERED_IDS,
            f"renumbered {renamed} of {len(nodes)} node ids to n1..n{len(nodes)} (see id_map)",
        )
        for node in nodes:
            node["id"] = id_map[node["id"]]
            if node["group_id"] is not None:
                node["group_id"] = id_map[node["group_id"]]
        for edge in edges:
            edge["source"] = id_map[edge["source"]]
            edge["target"] = id_map[edge["target"]]

    by_label: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        by_label[node["label"]].append(node["id"])
    for label, ids in by_label.items():
        if len(ids) > 1:
            note(
                NormalizationCode.FLAGGED_DUPLICATE_LABEL,
                f"label {label!r} is shared by nodes {', '.join(ids)} (kept as separate nodes)",
            )

    return NormalizationResult(
        graph=DiagramGraph.model_validate(data), changes=changes, id_map=id_map
    )
