"""Programmatic repair of model output that failed validation twice (spec §8 Stage C, step 2).

Deliberately conservative: it drops what cannot be kept, maps near-miss vocabulary values
("Flows To" → "flows_to"), and fixes group references. It never invents content — no new
nodes, labels, or edges. Every change is recorded as a ``RepairFix``; nothing is changed
silently.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas import SCHEMA_VERSION, DiagramType, Edge, Node, NodeType, Relation


class RepairCode(StrEnum):
    DROPPED_UNKNOWN_FIELD = "dropped_unknown_field"
    SET_SCHEMA_VERSION = "set_schema_version"
    MAPPED_VALUE = "mapped_value"  # case/spacing variant of an allowed value
    DEFAULTED_VALUE = "defaulted_value"  # disallowed value replaced by "unknown"/"other"
    COERCED_TO_STRING = "coerced_to_string"
    DROPPED_NODE = "dropped_node"
    DROPPED_DUPLICATE_NODE = "dropped_duplicate_node"
    DROPPED_EDGE = "dropped_edge"
    REPLACED_EDGES = "replaced_edges"  # missing or non-list "edges" → []
    CLEARED_GROUP_ID = "cleared_group_id"
    RETYPED_GROUP_CONTAINER = "retyped_group_container"
    BROKE_GROUP_CYCLE = "broke_group_cycle"
    CLEARED_VALUE = "cleared_value"  # optional text field of the wrong type → null
    DROPPED_METADATA = "dropped_metadata"  # invalid bbox/confidence


class RepairFix(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: RepairCode
    message: str


class RepairError(ValueError):
    """Nothing valid could be salvaged."""


_GRAPH_FIELDS = frozenset({"schema_version", "diagram_type", "nodes", "edges"})
_NODE_FIELDS = frozenset(Node.model_fields)
_EDGE_FIELDS = frozenset(Edge.model_fields)
_MISSING = object()


def repair_graph(data: Mapping[str, Any]) -> tuple[dict[str, Any], list[RepairFix]]:
    """A repaired copy of ``data`` and every fix applied. ``data`` is not modified."""
    return _Repair().run(data)


class _Repair:
    def __init__(self) -> None:
        self.fixes: list[RepairFix] = []

    def note(self, code: RepairCode, message: str) -> None:
        self.fixes.append(RepairFix(code=code, message=message))

    def run(self, data: Mapping[str, Any]) -> tuple[dict[str, Any], list[RepairFix]]:
        self._drop_unknown_fields(data, _GRAPH_FIELDS, "graph")
        schema_version = self._schema_version(data.get("schema_version", _MISSING))
        diagram_type = self._vocabulary(
            data.get("diagram_type", _MISSING), DiagramType, DiagramType.OTHER, "diagram_type"
        )
        nodes = self._nodes(data.get("nodes", _MISSING))
        self._fix_groups(nodes)
        edges = self._edges(data.get("edges", _MISSING), {node["id"] for node in nodes})
        graph = {
            "schema_version": schema_version,
            "diagram_type": diagram_type,
            "nodes": nodes,
            "edges": edges,
        }
        return graph, self.fixes

    # --- graph level --------------------------------------------------------------------

    def _drop_unknown_fields(self, item: Mapping[str, Any], allowed: frozenset, where: str) -> None:
        for key in item:
            if key not in allowed:
                self.note(
                    RepairCode.DROPPED_UNKNOWN_FIELD, f"{where}: dropped unknown field {key!r}"
                )

    def _schema_version(self, value: object) -> str:
        if value != SCHEMA_VERSION:
            self.note(
                RepairCode.SET_SCHEMA_VERSION,
                f"schema_version {_describe(value)} replaced with {SCHEMA_VERSION!r}",
            )
        return SCHEMA_VERSION

    def _vocabulary(
        self, value: object, vocabulary: type[StrEnum], fallback: StrEnum, where: str
    ) -> str:
        allowed = {member.value for member in vocabulary}
        if isinstance(value, str):
            if value in allowed:
                return value
            key = re.sub(r"[\s\-]+", "_", value.strip().lower())
            if key in allowed:
                self.note(RepairCode.MAPPED_VALUE, f"{where}: {value!r} mapped to {key!r}")
                return key
        self.note(
            RepairCode.DEFAULTED_VALUE,
            f"{where}: {_describe(value)} is not allowed; set to {fallback.value!r}",
        )
        return fallback.value

    def _as_text(self, value: object, where: str) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, int | float) and not isinstance(value, bool):
            text = str(value)
            self.note(RepairCode.COERCED_TO_STRING, f"{where}: {value!r} converted to {text!r}")
            return text
        return None

    # --- nodes --------------------------------------------------------------------------

    def _nodes(self, raw: object) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            raise RepairError(f"'nodes' is {_describe(raw)}, not a list")

        nodes: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, item in enumerate(raw):
            where = f"nodes[{index}]"
            if not isinstance(item, dict):
                self.note(RepairCode.DROPPED_NODE, f"{where}: not an object; dropped")
                continue
            self._drop_unknown_fields(item, _NODE_FIELDS, where)

            node_id = self._as_text(item.get("id"), f"{where}.id")
            if node_id is None or not node_id.strip():
                self.note(RepairCode.DROPPED_NODE, f"{where}: missing or empty id; dropped")
                continue
            where = f"nodes[{index}] ({node_id!r})"
            if node_id in seen:
                self.note(
                    RepairCode.DROPPED_DUPLICATE_NODE,
                    f"{where}: duplicate id; dropped, keeping the first node with this id",
                )
                continue
            label = self._as_text(item.get("label"), f"{where}.label")
            if label is None or not label.strip():
                self.note(RepairCode.DROPPED_NODE, f"{where}: missing or empty label; dropped")
                continue

            node: dict[str, Any] = {
                "id": node_id,
                "label": label,
                "type": self._vocabulary(
                    item.get("type", _MISSING), NodeType, NodeType.UNKNOWN, f"{where}.type"
                ),
                "group_id": self._group_id(item.get("group_id"), where),
            }
            node.update(self._metadata(item, where))
            seen.add(node_id)
            nodes.append(node)

        if not nodes:
            raise RepairError("no valid nodes remain")
        return nodes

    def _group_id(self, value: object, where: str) -> str | None:
        if value is None:
            return None
        text = self._as_text(value, f"{where}.group_id")
        if text is None or not text.strip():
            self.note(RepairCode.CLEARED_GROUP_ID, f"{where}.group_id: {_describe(value)}; cleared")
            return None
        return text

    def _metadata(self, item: Mapping[str, Any], where: str) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        bbox = item.get("bbox")
        if bbox is not None:
            if _is_valid_bbox(bbox):
                metadata["bbox"] = list(bbox)
            else:
                self.note(RepairCode.DROPPED_METADATA, f"{where}.bbox: invalid {bbox!r}; dropped")
        confidence = item.get("confidence")
        if confidence is not None:
            if _is_number(confidence) and 0.0 <= confidence <= 1.0:
                metadata["confidence"] = confidence
            else:
                self.note(
                    RepairCode.DROPPED_METADATA,
                    f"{where}.confidence: invalid {confidence!r}; dropped",
                )
        return metadata

    def _fix_groups(self, nodes: list[dict[str, Any]]) -> None:
        by_id = {node["id"]: node for node in nodes}
        position = {node["id"]: index for index, node in enumerate(nodes)}

        for node in nodes:
            group_id = node["group_id"]
            if group_id is None:
                continue
            if group_id == node["id"]:
                self.note(
                    RepairCode.CLEARED_GROUP_ID,
                    f"node {node['id']!r}: group_id pointed to itself; cleared",
                )
                node["group_id"] = None
            elif group_id not in by_id:
                self.note(
                    RepairCode.CLEARED_GROUP_ID,
                    f"node {node['id']!r}: group_id {group_id!r} is not an existing node; cleared",
                )
                node["group_id"] = None

        for node in nodes:
            path: list[str] = []
            current: str | None = node["id"]
            while current is not None and current not in path:
                path.append(current)
                current = by_id[current]["group_id"]
            if current is not None:
                cycle = path[path.index(current) :]
                breaker = min(cycle, key=position.__getitem__)
                self.note(
                    RepairCode.BROKE_GROUP_CYCLE,
                    f"group_id cycle {' -> '.join([*cycle, cycle[0]])}; "
                    f"cleared group_id of {breaker!r}",
                )
                by_id[breaker]["group_id"] = None

        for node in nodes:
            group_id = node["group_id"]
            if group_id is not None and by_id[group_id]["type"] != NodeType.GROUP.value:
                container = by_id[group_id]
                self.note(
                    RepairCode.RETYPED_GROUP_CONTAINER,
                    f"node {group_id!r} contains other nodes; type {container['type']!r} "
                    "changed to 'group'",
                )
                container["type"] = NodeType.GROUP.value

    # --- edges --------------------------------------------------------------------------

    def _edges(self, raw: object, node_ids: set[str]) -> list[dict[str, Any]]:
        if not isinstance(raw, list):
            self.note(RepairCode.REPLACED_EDGES, f"'edges' is {_describe(raw)}; set to []")
            return []

        edges: list[dict[str, Any]] = []
        for index, item in enumerate(raw):
            where = f"edges[{index}]"
            if not isinstance(item, dict):
                self.note(RepairCode.DROPPED_EDGE, f"{where}: not an object; dropped")
                continue
            self._drop_unknown_fields(item, _EDGE_FIELDS, where)

            source = self._as_text(item.get("source"), f"{where}.source")
            target = self._as_text(item.get("target"), f"{where}.target")
            dangling = [
                f"{end} {value!r}"
                for end, value in (("source", source), ("target", target))
                if value not in node_ids
            ]
            if dangling:
                self.note(
                    RepairCode.DROPPED_EDGE,
                    f"{where}: {' and '.join(dangling)} not an existing node; dropped",
                )
                continue

            edges.append(
                {
                    "source": source,
                    "target": target,
                    "relation": self._vocabulary(
                        item.get("relation", _MISSING),
                        Relation,
                        Relation.UNKNOWN,
                        f"{where}.relation",
                    ),
                    "label": self._optional_text(item.get("label"), f"{where}.label"),
                    "condition": self._optional_text(item.get("condition"), f"{where}.condition"),
                }
            )
        return edges

    def _optional_text(self, value: object, where: str) -> str | None:
        if value is None:
            return None
        text = self._as_text(value, where)
        if text is None:
            self.note(RepairCode.CLEARED_VALUE, f"{where}: {_describe(value)}; set to null")
        return text


def _describe(value: object) -> str:
    if value is _MISSING:
        return "missing"
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_valid_bbox(value: object) -> bool:
    if not isinstance(value, list | tuple) or len(value) != 4:
        return False
    if not all(_is_number(v) for v in value):
        return False
    x1, y1, x2, y2 = value
    return x2 >= x1 and y2 >= y1
