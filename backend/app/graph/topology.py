"""Graph construction and topology queries on NetworkX (spec §9).

``build_graph`` turns a validated ``DiagramGraph`` into a ``networkx.MultiDiGraph``: parallel
edges (e.g. two relations between the same nodes) are kept, so topology is preserved
exactly. Node attributes carry label, type, group_id (group membership, §7.1), optional
metadata, and ``order`` — the node's position in the diagram, used to keep every query's
output deterministic. All edges count for topology, whatever their relation.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable

import networkx as nx
from pydantic import BaseModel

from app.schemas import DiagramGraph, NodeType


def build_graph(diagram: DiagramGraph) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(
        schema_version=diagram.schema_version, diagram_type=diagram.diagram_type.value
    )
    for order, node in enumerate(diagram.nodes):
        graph.add_node(
            node.id,
            label=node.label,
            type=node.type.value,
            group_id=node.group_id,
            bbox=node.bbox,
            confidence=node.confidence,
            order=order,
        )
    for index, edge in enumerate(diagram.edges):
        graph.add_edge(
            edge.source,
            edge.target,
            key=index,
            relation=edge.relation.value,
            label=edge.label,
            condition=edge.condition,
        )
    return graph


# --- diagnostics ----------------------------------------------------------------------


class GraphDiagnostics(BaseModel):
    """Topology warnings; the schema already guarantees referential integrity."""

    is_dag: bool
    cycles: list[list[str]]  # up to MAX_REPORTED_CYCLES, each as a node sequence
    self_loops: list[str]
    isolated_nodes: list[str]  # no edges and not a pure group container
    component_count: int  # weakly connected, ignoring pure group containers
    sources: list[str]
    sinks: list[str]


MAX_REPORTED_CYCLES = 20


def validate_graph(graph: nx.MultiDiGraph) -> GraphDiagnostics:
    simple = nx.DiGraph(graph)
    cycles = [
        _ordered_cycle(graph, cycle)
        for cycle in itertools.islice(nx.simple_cycles(simple), MAX_REPORTED_CYCLES)
    ]
    containers = set(_pure_containers(graph))
    connected = graph.subgraph(n for n in graph if n not in containers)
    return GraphDiagnostics(
        is_dag=nx.is_directed_acyclic_graph(simple),
        cycles=sorted(cycles, key=lambda c: [_order(graph, n) for n in c]),
        self_loops=_sort(graph, {u for u, v in graph.edges() if u == v}),
        isolated_nodes=_sort(graph, (n for n in nx.isolates(graph) if n not in containers)),
        component_count=nx.number_weakly_connected_components(connected) if connected else 0,
        sources=find_sources(graph),
        sinks=find_sinks(graph),
    )


# --- neighbourhood and reachability ---------------------------------------------------


def find_predecessors(graph: nx.MultiDiGraph, node_id: str) -> list[str]:
    _require(graph, node_id)
    return _sort(graph, graph.predecessors(node_id))


def find_successors(graph: nx.MultiDiGraph, node_id: str) -> list[str]:
    _require(graph, node_id)
    return _sort(graph, graph.successors(node_id))


def find_sources(graph: nx.MultiDiGraph) -> list[str]:
    """Nodes with no incoming edges (pure group containers excluded)."""
    containers = set(_pure_containers(graph))
    return _sort(graph, (n for n in graph if graph.in_degree(n) == 0 and n not in containers))


def find_sinks(graph: nx.MultiDiGraph) -> list[str]:
    """Nodes with no outgoing edges (pure group containers excluded)."""
    containers = set(_pure_containers(graph))
    return _sort(graph, (n for n in graph if graph.out_degree(n) == 0 and n not in containers))


MAX_PATHS = 100


def find_paths(
    graph: nx.MultiDiGraph, source: str, target: str, *, limit: int = MAX_PATHS
) -> list[list[str]]:
    """Simple directed paths from source to target, shortest first, at most ``limit``."""
    _require(graph, source)
    _require(graph, target)
    paths = itertools.islice(nx.all_simple_paths(nx.DiGraph(graph), source, target), limit)
    return sorted(paths, key=lambda p: (len(p), [_order(graph, n) for n in p]))


# --- parallel branches ----------------------------------------------------------------


class ParallelBranches(BaseModel):
    """Branches leaving ``fork`` that run side by side until ``merge`` (None: never merge).

    Each branch lists its nodes strictly between fork and merge; an empty branch is a
    direct fork → merge edge, i.e. a skip connection.
    """

    fork: str
    merge: str | None
    branches: list[list[str]]


def find_parallel_branches(graph: nx.MultiDiGraph) -> list[ParallelBranches]:
    simple = nx.DiGraph(graph)
    found: list[ParallelBranches] = []
    for fork in _sort(graph, simple):
        starts = _sort(graph, (s for s in simple.successors(fork) if s != fork))
        if len(starts) < 2:
            continue
        reach = {s: nx.descendants(simple, s) | {s} for s in starts}
        candidates = {
            n for n in set().union(*reach.values()) if n != fork and _reached_by(n, reach) >= 2
        }
        # Earliest merge points: candidates not strictly downstream of another candidate.
        downstream = {c: nx.descendants(simple, c) for c in candidates}
        merges = [
            m
            for m in candidates
            if not any(o != m and m in downstream[o] and o not in downstream[m] for o in candidates)
        ]
        for merge in _sort(graph, merges):
            ancestors = nx.ancestors(simple, merge)
            branches = [
                _flow_sort(simple, graph, (reach[s] & ancestors) - {fork, merge})
                for s in starts
                if merge in reach[s]
            ]
            found.append(ParallelBranches(fork=fork, merge=merge, branches=branches))
        if not merges:
            exclusive = [
                _flow_sort(
                    simple, graph, reach[s] - set().union(*(reach[o] for o in starts if o != s))
                )
                for s in starts
            ]
            found.append(ParallelBranches(fork=fork, merge=None, branches=exclusive))
    return found


# --- groups ---------------------------------------------------------------------------


def find_group_members(
    graph: nx.MultiDiGraph, group_id: str, *, recursive: bool = False
) -> list[str]:
    """Nodes whose group_id is ``group_id``; with ``recursive``, nested members too."""
    _require(graph, group_id)
    members: list[str] = []
    frontier = [group_id]
    while frontier:
        parent = frontier.pop()
        children = [n for n, data in graph.nodes(data=True) if data["group_id"] == parent]
        members.extend(children)
        if recursive:
            frontier.extend(children)
    return _sort(graph, members)


def flatten_groups(diagram: DiagramGraph) -> DiagramGraph:
    """The same graph without nesting, for consumers that can't show groups.

    Clears every group_id and drops pure containers (group nodes without edges); group
    nodes that are edge endpoints stay, as ordinary nodes.
    """
    endpoints = {e.source for e in diagram.edges} | {e.target for e in diagram.edges}
    nodes = [
        node.model_copy(update={"group_id": None})
        for node in diagram.nodes
        if not (node.type is NodeType.GROUP and node.id not in endpoints)
    ]
    return diagram.model_copy(update={"nodes": nodes})


# --- helpers --------------------------------------------------------------------------


def _pure_containers(graph: nx.MultiDiGraph) -> Iterable[str]:
    return (
        n
        for n, data in graph.nodes(data=True)
        if data["type"] == NodeType.GROUP.value and graph.degree(n) == 0
    )


def _reached_by(node: str, reach: dict[str, set[str]]) -> int:
    return sum(node in nodes for nodes in reach.values())


def _order(graph: nx.MultiDiGraph, node_id: str) -> int:
    return graph.nodes[node_id]["order"]


def _sort(graph: nx.MultiDiGraph, node_ids: Iterable[str]) -> list[str]:
    return sorted(set(node_ids), key=lambda n: _order(graph, n))


def _flow_sort(simple: nx.DiGraph, graph: nx.MultiDiGraph, node_ids: Iterable[str]) -> list[str]:
    """Nodes in flow (topological) order, ties by diagram order; diagram order if cyclic."""
    sub = simple.subgraph(set(node_ids))
    if not nx.is_directed_acyclic_graph(sub):
        return _sort(graph, sub)
    return list(nx.lexicographical_topological_sort(sub, key=lambda n: _order(graph, n)))


def _ordered_cycle(graph: nx.MultiDiGraph, cycle: list[str]) -> list[str]:
    """Rotate a cycle to start at its earliest node, for stable output."""
    start = min(range(len(cycle)), key=lambda i: _order(graph, cycle[i]))
    return cycle[start:] + cycle[:start]


def _require(graph: nx.MultiDiGraph, node_id: str) -> None:
    if node_id not in graph:
        raise KeyError(f"unknown node id {node_id!r}")
