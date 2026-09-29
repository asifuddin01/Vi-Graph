"""Canonical diagram graph, schema version 2.0 (spec §7).

Validation implements the first-pass rejection rules of spec §8 Stage C. These models
only *validate* — they never modify their input. Normalization (whitespace, relation
names, duplicate edges, ...) is a separate step that logs every change (§8 Stage D),
and repair of invalid output is handled by the Stage C retry/repair path.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "2.0"
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})


class DiagramType(StrEnum):
    """Diagram kinds in scope (spec §1); scored by diagram-type accuracy (§20.8)."""

    NEURAL_NETWORK = "neural_network"
    ML_PIPELINE = "ml_pipeline"
    FLOWCHART = "flowchart"
    SYSTEM_ARCHITECTURE = "system_architecture"
    DATA_PIPELINE = "data_pipeline"
    SCIENTIFIC_WORKFLOW = "scientific_workflow"
    UML = "uml"
    OTHER = "other"


class NodeType(StrEnum):
    INPUT = "input"
    MODULE = "module"
    OPERATION = "operation"
    DECISION = "decision"
    FUSION = "fusion"
    OUTPUT = "output"
    GROUP = "group"  # a container; members point at it via group_id (§7.1)
    UNKNOWN = "unknown"


class Relation(StrEnum):
    """Edge relation vocabulary (spec §7.2)."""

    FLOWS_TO = "flows_to"  # default control/data flow
    CONTAINS = "contains"  # containment asserted without a visual boundary
    BRANCHES_TO = "branches_to"  # one-to-many split
    MERGES_TO = "merges_to"  # many-to-one join
    INHERITS_FROM = "inherits_from"  # UML generalization
    COMPOSES = "composes"  # UML composition
    AGGREGATES = "aggregates"  # UML aggregation
    DEPENDS_ON = "depends_on"  # UML/architecture dependency
    UNKNOWN = "unknown"  # relation present but type unclear from the image


class GraphStructureError(ValueError):
    """Cross-reference problems in a graph; ``problems`` lists each one."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("invalid graph structure:\n" + "\n".join(f"- {p}" for p in problems))


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be empty or whitespace-only")
    return value


NonBlankStr = Annotated[str, AfterValidator(_not_blank)]


def _is_none(value: object) -> bool:
    return value is None


class _StrictModel(BaseModel):
    # Unknown keys are validation errors rather than being silently dropped; the
    # repair step removes them and records that it did (§8 Stage C).
    model_config = ConfigDict(extra="forbid")


class Node(_StrictModel):
    id: NonBlankStr
    label: NonBlankStr
    type: NodeType
    group_id: NonBlankStr | None = None

    # Optional metadata (§7.3); left out of serialized output when unset.
    bbox: tuple[float, float, float, float] | None = Field(default=None, exclude_if=_is_none)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0, exclude_if=_is_none)

    @field_validator("bbox")
    @classmethod
    def _bbox_is_ordered(
        cls, bbox: tuple[float, float, float, float] | None
    ) -> tuple[float, float, float, float] | None:
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            if x2 < x1 or y2 < y1:
                raise ValueError("bbox must be [x1, y1, x2, y2] with x2 >= x1 and y2 >= y1")
        return bbox


class Edge(_StrictModel):
    source: NonBlankStr
    target: NonBlankStr
    relation: Relation
    label: str | None = None  # visible edge text, e.g. "Yes"/"No" on a decision branch
    condition: str | None = None  # structured condition, e.g. "x > 0"


class DiagramGraph(_StrictModel):
    schema_version: Literal["2.0"]
    diagram_type: DiagramType
    nodes: list[Node] = Field(min_length=1)
    edges: list[Edge]

    @field_validator("schema_version", mode="before")
    @classmethod
    def _schema_version_is_supported(cls, value: object) -> object:
        if value not in SUPPORTED_SCHEMA_VERSIONS:
            supported = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS))
            raise ValueError(f"unsupported schema_version {value!r} (supported: {supported})")
        return value

    @model_validator(mode="after")
    def _structure_is_valid(self) -> Self:
        problems = _structural_problems(self.nodes, self.edges)
        if problems:
            raise GraphStructureError(problems)
        return self


def _structural_problems(nodes: Sequence[Node], edges: Sequence[Edge]) -> list[str]:
    """Every cross-reference problem in the graph, so a retry prompt can list them all."""
    problems: list[str] = []

    id_counts = Counter(node.id for node in nodes)
    for node_id, count in id_counts.items():
        if count > 1:
            problems.append(f"duplicate node id '{node_id}' is used by {count} nodes")

    by_id = {node.id: node for node in nodes}

    for index, edge in enumerate(edges):
        for end in dict.fromkeys((edge.source, edge.target)):
            if end not in by_id:
                problems.append(
                    f"edge #{index} '{edge.source}->{edge.target}' references node id "
                    f"'{end}', which does not exist"
                )

    parent_of: dict[str, str] = {}
    for node in nodes:
        group_id = node.group_id
        if group_id is None:
            continue
        if group_id == node.id:
            problems.append(f"node '{node.id}' has group_id pointing to itself")
        elif group_id not in by_id:
            problems.append(
                f"node '{node.id}' has group_id '{group_id}', which is not an existing node id"
            )
        else:
            parent_type = by_id[group_id].type
            if parent_type is not NodeType.GROUP:
                problems.append(
                    f"node '{node.id}' has group_id '{group_id}', but node '{group_id}' has "
                    f"type '{parent_type}' instead of 'group'"
                )
            parent_of[node.id] = group_id

    problems.extend(_containment_cycles(parent_of))
    return problems


def _containment_cycles(parent_of: dict[str, str]) -> list[str]:
    problems: list[str] = []
    reported: set[frozenset[str]] = set()
    for start in parent_of:
        path: list[str] = []
        current = start
        while current in parent_of and current not in path:
            path.append(current)
            current = parent_of[current]
        if current in path:
            cycle = path[path.index(current) :]
            if frozenset(cycle) not in reported:
                reported.add(frozenset(cycle))
                problems.append("group_id containment cycle: " + " -> ".join([*cycle, cycle[0]]))
    return problems
