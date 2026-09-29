"""Random diagram graphs built from pattern operators (spec §13 patterns, §14 levels).

A graph grows from a source by applying operators — chain, parallel branches, residual and
skip connections, decisions, loops, fan-in — each adding a known structure and recording
its pattern name, so every sample says exactly which patterns it contains (for per-pattern
error analysis). Passes then add groups (nesting), long-range edges, edge labels, and
dependency relations. The node budget is fixed up front, so every graph lands inside its
difficulty level's range. The result is validated against the canonical schema.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

import networkx as nx
from pydantic import BaseModel

from app.schemas import DiagramGraph
from data.generator.vocab import EDGE_LABELS, UML_CLASSES, VOCABULARIES, LabelSource

GENERATOR_VERSION = "1"

# §14: component (non-group) node count per difficulty level. Level 4 is "25+"; capped so
# diagrams stay renderable at a legible size.
LEVELS: dict[int, tuple[int, int]] = {1: (3, 6), 2: (6, 12), 3: (12, 25), 4: (25, 40)}

FLOW_TYPES = [
    "neural_network",
    "flowchart",
    "data_pipeline",
    "ml_pipeline",
    "scientific_workflow",
    "system_architecture",
]
DIAGRAM_TYPES = [*FLOW_TYPES, "uml"]

_ROLE_TYPES = {
    "source": "input",
    "step": "module",
    "op": "operation",
    "fusion": "fusion",
    "decision": "decision",
    "sink": "output",
    "group": "group",
}


class GraphSpec(BaseModel):
    """What a generated graph contains; stored with each sample."""

    level: int
    diagram_type: str
    patterns: list[str]
    n_nodes: int  # components, excluding group containers
    n_groups: int
    group_depth: int
    n_edges: int
    n_labeled_edges: int
    has_cycle: bool
    depth: int  # nodes on the longest path (of the condensation, if cyclic)
    max_fan_out: int
    max_fan_in: int


@dataclass
class GeneratedGraph:
    graph: DiagramGraph
    spec: GraphSpec


@dataclass
class _Builder:
    rng: random.Random
    diagram_type: str
    level: int
    labels: LabelSource
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    patterns: set[str] = field(default_factory=set)
    blocks: list[list[str]] = field(default_factory=list)  # node ids created per operator

    @property
    def components(self) -> int:
        return sum(1 for n in self.nodes if n["type"] != "group")

    def node(self, role: str, label: str | None = None) -> str:
        node_id = f"n{len(self.nodes) + 1}"
        if label is None:
            label = self._repeat_label(role) or self.labels.draw(role)
        self.nodes.append(
            {"id": node_id, "label": label, "type": _ROLE_TYPES[role], "group_id": None}
        )
        return node_id

    def edge(self, source: str, target: str, label: str | None = None) -> None:
        entry = {
            "source": source,
            "target": target,
            "relation": "flows_to",
            "label": label,
            "condition": None,
        }
        if entry not in self.edges:
            self.edges.append(entry)

    def step_role(self) -> str:
        return "op" if self.rng.random() < 0.3 else "step"

    def _repeat_label(self, role: str) -> str | None:
        # Real architectures repeat labels (two "Conv 3x3"s); matching must cope with it.
        if self.diagram_type != "neural_network" or self.level < 2 or role not in {"step", "op"}:
            return None
        same_role = [n["label"] for n in self.nodes if n["type"] == _ROLE_TYPES[role]]
        if same_role and self.rng.random() < 0.12:
            self.patterns.add("repeated_labels")
            return self.rng.choice(same_role)
        return None


# --- operators: (builder, tail, budget) -> new tail, or None if it doesn't fit -----------

Operator = Callable[[_Builder, str, int], str | None]


def _chain(b: _Builder, tail: str, budget: int) -> str:
    for _ in range(min(budget, b.rng.randint(1, 2 if b.level == 1 else 3))):
        new = b.node(b.step_role())
        b.edge(tail, new)
        tail = new
    b.patterns.add("linear")
    return tail


def _parallel(b: _Builder, tail: str, budget: int) -> str | None:
    max_branches = 2 if b.level <= 2 else min(4, b.level + 1)
    max_length = {1: 1, 2: 2}.get(b.level, 3)
    branches = b.rng.randint(2, max_branches)
    lengths = [b.rng.randint(1, max_length) for _ in range(branches)]
    while sum(lengths) + 1 > budget and (branches > 2 or max(lengths) > 1):
        if max(lengths) > 1:
            lengths[lengths.index(max(lengths))] -= 1
        else:
            branches -= 1
            lengths.pop()
    if sum(lengths) + 1 > budget:
        return None
    ends = []
    for length in lengths:
        current = tail
        for _ in range(length):
            new = b.node(b.step_role())
            b.edge(current, new)
            current = new
        ends.append(current)
    merge = b.node("fusion")
    for end in ends:
        b.edge(end, merge)
    b.patterns |= {"branching", "merging"}
    if len(lengths) >= 3:
        b.patterns.add("multi_branch")
    return merge


def _residual(b: _Builder, tail: str, budget: int) -> str | None:
    length = b.rng.randint(2, 3)
    if length + 1 > budget:
        return None
    current = tail
    for _ in range(length):
        new = b.node(b.step_role())
        b.edge(current, new)
        current = new
    add = b.node("fusion", label=b.rng.choice(["Add", "Add", "+", "Sum"]))
    b.edge(current, add)
    b.edge(tail, add)  # the identity shortcut
    b.patterns |= {"skip", "residual"}
    return add


def _skip(b: _Builder, tail: str, budget: int) -> str | None:
    length = b.rng.randint(2, 3)
    if length > budget:
        return None
    current = tail
    for _ in range(length):
        new = b.node(b.step_role())
        b.edge(current, new)
        current = new
    b.edge(tail, current)
    b.patterns.add("skip")
    return current


def _decision(b: _Builder, tail: str, budget: int) -> str | None:
    yes, no = b.rng.randint(1, 2), b.rng.randint(1, 2)
    while 1 + yes + no + 1 > budget and (yes > 1 or no > 1):
        yes, no = (yes - 1, no) if yes >= no else (yes, no - 1)
    if 1 + yes + no + 1 > budget:
        return None
    decision = b.node("decision")
    b.edge(tail, decision)
    ends = []
    for label, length in (("Yes", yes), ("No", no)):
        current, first = decision, True
        for _ in range(length):
            new = b.node(b.step_role())
            b.edge(current, new, label=label if first else None)
            current, first = new, False
        ends.append(current)
    join = b.node("step")
    for end in ends:
        b.edge(end, join)
    b.patterns |= {"decision", "labeled_edges", "branching", "merging"}
    return join


def _loop(b: _Builder, tail: str, budget: int) -> str | None:
    if budget < 3:
        return None
    work = b.node("step")
    b.edge(tail, work)
    check = b.node("decision")
    b.edge(work, check)
    b.edge(check, work, label="No")  # back edge
    after = b.node("step")
    b.edge(check, after, label="Yes")
    b.patterns |= {"cycle", "decision", "labeled_edges"}
    return after


def _fan_in(b: _Builder, tail: str, budget: int) -> str | None:
    extra = b.rng.randint(1, 2)
    if extra + 1 > budget:
        extra = budget - 1
    if extra < 1:
        return None
    join = b.node("fusion")
    b.edge(tail, join)
    for _ in range(extra):
        source = b.node("source")
        b.edge(source, join)
    b.patterns |= {"fan_in", "merging"}
    return join


# Operator weights per diagram type; the level decides which are allowed at all.
_WEIGHTS: dict[str, dict[str, float]] = {
    "neural_network": {"chain": 3, "parallel": 2, "residual": 2, "skip": 1, "fan_in": 1},
    "flowchart": {"chain": 3, "decision": 3, "loop": 2, "parallel": 1},
    "data_pipeline": {"chain": 3, "parallel": 2, "fan_in": 2, "decision": 1, "loop": 0.5},
    "ml_pipeline": {"chain": 3, "parallel": 2, "fan_in": 1, "decision": 1, "loop": 1},
    "scientific_workflow": {"chain": 3, "parallel": 2, "fan_in": 1, "decision": 1, "loop": 0.5},
    "system_architecture": {"chain": 2, "parallel": 3, "fan_in": 1, "decision": 0.5},
}
_OPERATORS: dict[str, Operator] = {
    "chain": _chain,
    "parallel": _parallel,
    "residual": _residual,
    "skip": _skip,
    "decision": _decision,
    "loop": _loop,
    "fan_in": _fan_in,
}
_ALLOWED_BY_LEVEL = {
    1: {"chain", "parallel"},
    2: {"chain", "parallel", "residual", "skip", "decision", "fan_in"},
    3: set(_OPERATORS),
    4: set(_OPERATORS),
}


def generate_graph(rng: random.Random, level: int, diagram_type: str) -> GeneratedGraph:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level}")
    if diagram_type == "uml":
        builder = _uml(rng, level)
    elif diagram_type in FLOW_TYPES:
        builder = _flow(rng, level, diagram_type)
    else:
        raise ValueError(f"unknown diagram type {diagram_type!r}")
    graph = DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": diagram_type,
            "nodes": builder.nodes,
            "edges": builder.edges,
        }
    )
    return GeneratedGraph(graph=graph, spec=_describe(graph, level, builder.patterns))


def _flow(rng: random.Random, level: int, diagram_type: str) -> _Builder:
    low, high = LEVELS[level]
    target = rng.randint(low, high)
    b = _Builder(rng, diagram_type, level, LabelSource(rng, VOCABULARIES[diagram_type]))
    sinks = rng.randint(2, 3) if level >= 2 and rng.random() < 0.25 else 1

    tail = b.node("source")
    weights = {
        name: weight
        for name, weight in _WEIGHTS[diagram_type].items()
        if name in _ALLOWED_BY_LEVEL[level]
    }
    while b.components < target - sinks:
        budget = target - sinks - b.components
        name = rng.choices(list(weights), weights=list(weights.values()))[0]
        before = len(b.nodes)
        new_tail = _OPERATORS[name](b, tail, budget)
        if new_tail is None:
            continue
        b.blocks.append([n["id"] for n in b.nodes[before:]])
        tail = new_tail

    for _ in range(sinks):
        b.edge(tail, b.node("sink"))
    if sinks > 1:
        b.patterns.add("fan_out")

    if level >= 2:
        _add_groups(b)
    if level >= 3 and rng.random() < 0.5:
        _add_long_range_edge(b)
    _add_edge_labels(b)
    if diagram_type == "system_architecture":
        _add_dependencies(b)
    return b


def _add_groups(b: _Builder) -> None:
    """Wrap some operator blocks in groups (§13 nested components); nest two at level 3+."""
    probability = {2: 0.25, 3: 0.35, 4: 0.4}[b.level]
    groups: list[str] = []
    for block in b.blocks:
        if len(block) >= 2 and b.rng.random() < probability:
            group = b.node("group")
            for node in b.nodes:
                if node["id"] in block:
                    node["group_id"] = group
            groups.append(group)
    if groups:
        b.patterns.add("nested")
    if b.level >= 3 and len(groups) >= 2 and b.rng.random() < 0.5:
        start = b.rng.randrange(len(groups) - 1)
        parent = b.node("group")
        for node in b.nodes:
            if node["id"] in groups[start : start + 2]:
                node["group_id"] = parent
        b.patterns.add("nested_deep")


def _add_long_range_edge(b: _Builder) -> None:
    graph = nx.DiGraph([(e["source"], e["target"]) for e in b.edges])
    components = [n["id"] for n in b.nodes if n["type"] != "group"]
    third = max(1, len(components) // 3)
    early = [n for n in components[:third] if graph.out_degree(n) > 0]
    late = [n for n in components[-third:] if graph.in_degree(n) > 0]
    b.rng.shuffle(early)
    for source in early:
        for target in late:
            if (
                source != target
                and not graph.has_edge(source, target)
                and not nx.has_path(graph, target, source)
            ):
                b.edge(source, target)
                b.patterns.add("long_range")
                return


def _add_edge_labels(b: _Builder) -> None:
    vocabulary = EDGE_LABELS.get(b.diagram_type)
    if not vocabulary or b.level < 3:
        return
    for edge in b.edges:
        if edge["label"] is None and b.rng.random() < 0.12:
            edge["label"] = b.rng.choice(vocabulary)
            b.patterns.add("labeled_edges")


def _add_dependencies(b: _Builder) -> None:
    for edge in b.edges:
        if edge["label"] is None and b.rng.random() < 0.15:
            edge["relation"] = "depends_on"
            b.patterns.add("dependency")


def _uml(rng: random.Random, level: int) -> _Builder:
    low, high = LEVELS[level]
    b = _Builder(rng, "uml", level, LabelSource(rng, {}))
    for name in rng.sample(UML_CLASSES, rng.randint(low, high)):
        b.node("step", label=name)
    ids = [n["id"] for n in b.nodes]
    pairs: set[tuple[str, str]] = set()
    graph = nx.DiGraph()
    graph.add_nodes_from(ids)

    def link(source: str, target: str, relation: str) -> None:
        if source == target or (source, target) in pairs or (target, source) in pairs:
            return
        if level <= 2 and nx.has_path(graph, target, source):
            return  # levels 1–2 stay acyclic (§14: simple layouts)
        pairs.add((source, target))
        graph.add_edge(source, target)
        b.edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "label": None,
                "condition": None,
            }
        )

    for index in range(1, len(ids)):  # an inheritance forest: child → parent
        if rng.random() < 0.4:
            link(ids[index], ids[rng.randrange(index)], "inherits_from")
    for _ in range(max(1, len(ids) // 2 + rng.randint(0, 2))):
        source, target = rng.sample(ids, 2)
        link(source, target, rng.choice(["composes", "aggregates", "depends_on"]))
    names = {
        "inherits_from": "inheritance",
        "composes": "composition",
        "aggregates": "aggregation",
        "depends_on": "dependency",
    }
    b.patterns |= {names[e["relation"]] for e in b.edges}
    return b


def _describe(graph: DiagramGraph, level: int, patterns: set[str]) -> GraphSpec:
    simple = nx.DiGraph()
    components = [n.id for n in graph.nodes if n.type.value != "group"]
    simple.add_nodes_from(n.id for n in graph.nodes)
    simple.add_edges_from((e.source, e.target) for e in graph.edges)
    condensed = nx.condensation(simple)
    parents = {n.id: n.group_id for n in graph.nodes}

    def nesting(node_id: str) -> int:
        depth, current = 0, parents[node_id]
        while current is not None:
            depth, current = depth + 1, parents[current]
        return depth

    return GraphSpec(
        level=level,
        diagram_type=graph.diagram_type.value,
        patterns=sorted(patterns),
        n_nodes=len(components),
        n_groups=len(graph.nodes) - len(components),
        group_depth=max((nesting(n.id) for n in graph.nodes), default=0),
        n_edges=len(graph.edges),
        n_labeled_edges=sum(1 for e in graph.edges if e.label),
        has_cycle=not nx.is_directed_acyclic_graph(simple),
        depth=len(nx.dag_longest_path(condensed)) if condensed.number_of_nodes() else 0,
        max_fan_out=max((simple.out_degree(n) for n in components), default=0),
        max_fan_in=max((simple.in_degree(n) for n in components), default=0),
    )
