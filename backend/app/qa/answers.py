"""Answers computed from the graph alone (spec §12: direct, structural, comparative,
explanation questions), each grounded in the node and edge ids it relied on.

``complete=False`` marks an answer the graph can't finish on its own (the "why" of a
connection), so the QA engine consults the image.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import networkx as nx
from pydantic import BaseModel

from app.graph import (
    find_group_members,
    find_parallel_branches,
    find_paths,
    find_predecessors,
    find_sinks,
    find_sources,
    find_successors,
    validate_graph,
)
from app.qa.entities import Mention, unique_nodes
from app.schemas import DiagramGraph, NodeType

MAX_PATHS_LISTED = 5
MAX_FLOW_SENTENCES = 14


class Grounding(BaseModel):
    nodes: list[str] = []
    edges: list[tuple[str, str]] = []


class GraphAnswer(BaseModel):
    text: str
    grounding: Grounding
    complete: bool = True


@dataclass
class _Context:
    diagram: DiagramGraph
    graph: nx.MultiDiGraph
    mentioned: list[str]

    def __post_init__(self) -> None:
        self.simple = nx.DiGraph(self.graph)
        self.labels = Counter(data["label"] for _, data in self.graph.nodes(data=True))

    def name(self, node_id: str) -> str:
        label = self.graph.nodes[node_id]["label"]
        return f"{label} ({node_id})" if self.labels[label] > 1 else label

    def names(self, node_ids: Iterable[str]) -> str:
        return join([self.name(n) for n in node_ids])

    def is_container(self, node_id: str) -> bool:
        return self.graph.nodes[node_id]["type"] == NodeType.GROUP.value

    def components(self) -> list[str]:
        return [n for n in self.graph if not self.is_container(n)]

    def grounded(
        self, nodes: Iterable[str], edges: Iterable[tuple[str, str]] | None = None
    ) -> Grounding:
        node_list = list(dict.fromkeys(nodes))
        if edges is None:  # every edge among the grounded nodes
            chosen = set(node_list)
            edges = [(u, v) for u, v in self.simple.edges() if u in chosen and v in chosen]
        return Grounding(nodes=node_list, edges=list(dict.fromkeys(edges)))


def answer_from_graph(
    intent: str, diagram: DiagramGraph, graph: nx.MultiDiGraph, mentions: list[Mention]
) -> GraphAnswer | None:
    """The graph's answer for ``intent``, or None when the graph can't answer it at all."""
    handler = _HANDLERS.get(intent)
    if handler is None:
        return None
    return handler(_Context(diagram, graph, unique_nodes(mentions)))


def join(items: list[str]) -> str:
    if not items:
        return "nothing"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _needs_node(ctx: _Context) -> GraphAnswer:
    listed = ctx.names(ctx.components()[:12])
    return GraphAnswer(
        text=f"I couldn't tell which node you mean. The nodes are: {listed}.",
        grounding=Grounding(),
    )


# --- direct ---------------------------------------------------------------------------

_TYPE_NAMES = {"fusion": "fusion node", "unknown": "node of unknown type", "group": "group"}


def _count_nodes(ctx: _Context) -> GraphAnswer:
    components = ctx.components()
    by_type = Counter(ctx.graph.nodes[n]["type"] for n in components)
    parts = [_plural(count, _TYPE_NAMES.get(t, t)) for t, count in by_type.items()]
    text = f"The diagram has {_plural(len(components), 'node')}: {join(parts)}."
    groups = [n for n in ctx.graph if ctx.is_container(n)]
    if groups:
        text += f" They are organized in {_plural(len(groups), 'group')} ({ctx.names(groups)})."
    return GraphAnswer(text=text, grounding=ctx.grounded(components, edges=[]))


def _count_edges(ctx: _Context) -> GraphAnswer:
    count = ctx.graph.number_of_edges()
    return GraphAnswer(
        text=f"The diagram has {_plural(count, 'connection')}.",
        grounding=ctx.grounded(ctx.graph.nodes, edges=list(ctx.simple.edges())),
    )


def _successors(ctx: _Context) -> GraphAnswer:
    if not ctx.mentioned:
        return _needs_node(ctx)
    sentences, nodes, edges = [], [], []
    for node in ctx.mentioned:
        after = find_successors(ctx.graph, node)
        nodes += [node, *after]
        edges += [(node, s) for s in after]
        if after:
            sentences.append(f"After {ctx.name(node)}, the flow goes to {ctx.names(after)}.")
        else:
            sentences.append(f"{ctx.name(node)} has no outgoing connections; it is a final output.")
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes, edges))


def _predecessors(ctx: _Context) -> GraphAnswer:
    if not ctx.mentioned:
        return _needs_node(ctx)
    sentences, nodes, edges = [], [], []
    for node in ctx.mentioned:
        before = find_predecessors(ctx.graph, node)
        nodes += [node, *before]
        edges += [(p, node) for p in before]
        if before:
            sentences.append(f"{ctx.name(node)} receives input from {ctx.names(before)}.")
        else:
            sentences.append(f"Nothing feeds into {ctx.name(node)}; it is an input.")
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes, edges))


def _sources(ctx: _Context) -> GraphAnswer:
    sources = [n for n in find_sources(ctx.graph)]
    if not sources:
        return GraphAnswer(
            text="Every node has an incoming connection (the graph is cyclic), so there is "
            "no single starting point.",
            grounding=Grounding(),
        )
    noun = "input is" if len(sources) == 1 else "inputs are"
    return GraphAnswer(
        text=f"The {noun} {ctx.names(sources)}.", grounding=ctx.grounded(sources, [])
    )


def _sinks(ctx: _Context) -> GraphAnswer:
    sinks = find_sinks(ctx.graph)
    if not sinks:
        return GraphAnswer(
            text="Every node has an outgoing connection (the graph is cyclic), so there is "
            "no final output.",
            grounding=Grounding(),
        )
    noun = "final output is" if len(sinks) == 1 else "final outputs are"
    return GraphAnswer(text=f"The {noun} {ctx.names(sinks)}.", grounding=ctx.grounded(sinks, []))


# --- structural -----------------------------------------------------------------------


def _neighbors(ctx: _Context) -> GraphAnswer:
    if not ctx.mentioned:
        return _needs_node(ctx)
    sentences, nodes, edges = [], [], []
    for node in ctx.mentioned:
        before = find_predecessors(ctx.graph, node)
        after = find_successors(ctx.graph, node)
        nodes += [node, *before, *after]
        edges += [(p, node) for p in before] + [(node, s) for s in after]
        parts = []
        if before:
            parts.append(f"receives input from {ctx.names(before)}")
        if after:
            parts.append(f"sends output to {ctx.names(after)}")
        if parts:
            sentences.append(f"{ctx.name(node)} {' and '.join(parts)}.")
        else:
            sentences.append(f"{ctx.name(node)} has no connections.")
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes, edges))


def _parallel(ctx: _Context) -> GraphAnswer:
    found = _relevant_branches(ctx)
    if not found:
        return GraphAnswer(
            text="There are no parallel branches; the flow is linear.", grounding=Grounding()
        )
    sentences, nodes = [], []
    for item in found:
        described = [_branch_text(ctx, b) for b in item.branches]
        nodes += [item.fork, *(n for b in item.branches for n in b)]
        if item.merge is None:
            sentences.append(
                f"After {ctx.name(item.fork)}, the flow splits into {join(described)}, "
                "which run in parallel and do not rejoin."
            )
        else:
            nodes.append(item.merge)
            sentences.append(
                f"After {ctx.name(item.fork)}, {join(described)} run in parallel and merge at "
                f"{ctx.name(item.merge)}."
            )
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes))


def _paths(ctx: _Context) -> GraphAnswer:
    if len(ctx.mentioned) >= 2:
        pairs = [(ctx.mentioned[0], ctx.mentioned[-1])]
    elif len(ctx.mentioned) == 1:
        node = ctx.mentioned[0]
        sources = find_sources(ctx.graph)
        pairs = (
            [(node, sink) for sink in find_sinks(ctx.graph) if sink != node]
            if node in sources
            else [(source, node) for source in sources]
        )
    else:
        pairs = [(s, t) for s in find_sources(ctx.graph) for t in find_sinks(ctx.graph) if s != t]
    if not pairs:
        return GraphAnswer(
            text="There are no start and end points to connect.", grounding=Grounding()
        )

    sentences, nodes, edges = [], [], []
    for source, target in pairs:
        paths = find_paths(ctx.graph, source, target)
        if not paths:
            sentences.append(f"There is no path from {ctx.name(source)} to {ctx.name(target)}.")
            continue
        shown = paths[:MAX_PATHS_LISTED]
        for path in shown:
            nodes += path
            edges += list(zip(path, path[1:], strict=False))
        rendered = "; ".join(" → ".join(ctx.name(n) for n in p) for p in shown)
        more = f" (showing {len(shown)})" if len(paths) > len(shown) else ""
        sentences.append(
            f"There {'is 1 path' if len(paths) == 1 else f'are {len(paths)} paths'} from "
            f"{ctx.name(source)} to {ctx.name(target)}{more}: {rendered}."
        )
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes, edges))


def _fan_out(ctx: _Context) -> GraphAnswer:
    hubs = [n for n in ctx.graph if len(find_successors(ctx.graph, n)) > 1]
    if not hubs:
        return GraphAnswer(text="No node has more than one outgoing edge.", grounding=Grounding())
    parts = [f"{ctx.name(n)} (to {ctx.names(find_successors(ctx.graph, n))})" for n in hubs]
    edges = [(n, s) for n in hubs for s in find_successors(ctx.graph, n)]
    return GraphAnswer(
        text=f"Nodes with multiple outgoing edges: {join(parts)}.",
        grounding=ctx.grounded([n for e in edges for n in e], edges),
    )


def _fan_in(ctx: _Context) -> GraphAnswer:
    hubs = [n for n in ctx.graph if len(find_predecessors(ctx.graph, n)) > 1]
    if not hubs:
        return GraphAnswer(text="No node has more than one incoming edge.", grounding=Grounding())
    parts = [f"{ctx.name(n)} (from {ctx.names(find_predecessors(ctx.graph, n))})" for n in hubs]
    edges = [(p, n) for n in hubs for p in find_predecessors(ctx.graph, n)]
    return GraphAnswer(
        text=f"Nodes that merge several inputs: {join(parts)}.",
        grounding=ctx.grounded([n for e in edges for n in e], edges),
    )


def _group_members(ctx: _Context) -> GraphAnswer:
    groups = [n for n in ctx.mentioned if ctx.is_container(n)] or (
        [] if ctx.mentioned else [n for n in ctx.graph if ctx.is_container(n)]
    )
    if not groups:
        if ctx.mentioned:
            node = ctx.mentioned[0]
            parent = ctx.graph.nodes[node]["group_id"]
            where = f"; it is inside {ctx.name(parent)}" if parent else ""
            return GraphAnswer(
                text=f"{ctx.name(node)} is not a group{where}.",
                grounding=ctx.grounded([node, *([parent] if parent else [])], []),
            )
        return GraphAnswer(text="The diagram has no groups.", grounding=Grounding())
    sentences, nodes = [], []
    for group in groups:
        members = find_group_members(ctx.graph, group)
        nested = find_group_members(ctx.graph, group, recursive=True)
        nodes += [group, *nested]
        extra = (
            f" ({len(nested) - len(members)} more nested inside)"
            if len(nested) > len(members)
            else ""
        )
        sentences.append(f"{ctx.name(group)} contains {ctx.names(members)}{extra}.")
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes))


def _cycles(ctx: _Context) -> GraphAnswer:
    report = validate_graph(ctx.graph)
    if report.is_dag:
        return GraphAnswer(text="The graph has no cycles; it is acyclic.", grounding=Grounding())
    shown = report.cycles[:3]
    rendered = "; ".join(" → ".join(ctx.name(n) for n in [*c, c[0]]) for c in shown)
    edges = [(c[i], c[(i + 1) % len(c)]) for c in shown for i in range(len(c))]
    count = len(report.cycles)
    return GraphAnswer(
        text=f"The graph has {_plural(count, 'cycle')}{'+' if count >= 20 else ''}: {rendered}.",
        grounding=ctx.grounded([n for c in shown for n in c], edges),
    )


# --- comparative ----------------------------------------------------------------------


def _deeper_branch(ctx: _Context) -> GraphAnswer:
    found = [p for p in _relevant_branches(ctx) if len(p.branches) >= 2]
    if not found:
        return GraphAnswer(text="There are no parallel branches to compare.", grounding=Grounding())
    sentences, nodes = [], []
    for item in found:
        depths = [(_depth(ctx, b), b) for b in item.branches]
        deepest = max(d for d, _ in depths)
        end = f" to {ctx.name(item.merge)}" if item.merge else ""
        nodes += [item.fork, *([item.merge] if item.merge else [])]
        if all(d == deepest for d, _ in depths):
            sentences.append(
                f"The branches from {ctx.name(item.fork)}{end} are equally deep "
                f"({_plural(deepest, 'step')} each)."
            )
            nodes += [n for _, b in depths for n in b]
            continue
        winner = next(b for d, b in depths if d == deepest)
        others = [
            f"{_branch_text(ctx, b)} ({_plural(d, 'step')})" for d, b in depths if b is not winner
        ]
        nodes += winner
        sentences.append(
            f"Of the branches from {ctx.name(item.fork)}{end}, the one through "
            f"{_branch_text(ctx, winner)} is deeper ({_plural(deepest, 'step')}) than "
            f"{join(others)}."
        )
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes))


def _common_successor(ctx: _Context) -> GraphAnswer:
    merges = [p for p in _relevant_branches(ctx) if p.merge is not None]
    if not merges:
        return _fan_in(ctx)
    sentences, nodes, edges = [], [], []
    for item in merges:
        inputs = [
            p
            for p in find_predecessors(ctx.graph, item.merge)
            if p == item.fork or any(p in b for b in item.branches)
        ]
        nodes += [item.merge, *inputs]
        edges += [(p, item.merge) for p in inputs]
        sentences.append(
            f"{ctx.name(item.merge)} receives the outputs of the branches from "
            f"{ctx.name(item.fork)}: {ctx.names(inputs)}."
        )
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes, edges))


def _longest_path(ctx: _Context) -> GraphAnswer:
    if not nx.is_directed_acyclic_graph(ctx.simple):
        return GraphAnswer(
            text="The graph contains cycles, so there is no well-defined longest path.",
            grounding=Grounding(),
        )
    path = nx.dag_longest_path(ctx.simple)
    if len(path) < 2:
        return GraphAnswer(text="The graph has no connected path.", grounding=Grounding())
    return GraphAnswer(
        text=f"The longest path has {len(path)} nodes: {' → '.join(ctx.name(n) for n in path)}.",
        grounding=ctx.grounded(path, list(zip(path, path[1:], strict=False))),
    )


# --- explanation ----------------------------------------------------------------------


def _explain_flow(ctx: _Context) -> GraphAnswer:
    order = _flow_order(ctx)
    sentences: list[str] = []
    sources = [n for n in find_sources(ctx.graph) if not ctx.is_container(n)]
    if sources:
        sentences.append(f"The diagram starts at {ctx.names(sources)}.")
    for node in order:
        before = [p for p in find_predecessors(ctx.graph, node) if p != node]
        after = [s for s in find_successors(ctx.graph, node) if s != node]
        if len(before) > 1:
            sentences.append(f"{ctx.names(before)} are combined at {ctx.name(node)}.")
        if len(after) > 1:
            sentences.append(f"{ctx.name(node)} branches into {ctx.names(after)}.")
        elif len(after) == 1 and len(find_predecessors(ctx.graph, after[0])) <= 1:
            sentences.append(f"{ctx.name(node)} feeds {ctx.name(after[0])}.")
    if not nx.is_directed_acyclic_graph(ctx.simple):
        sentences.append("The flow contains cycles.")
    sinks = [n for n in find_sinks(ctx.graph) if not ctx.is_container(n)]
    if sinks:
        sentences.append(
            f"The final output is {ctx.names(sinks)}."
            if len(sinks) == 1
            else f"The final outputs are {ctx.names(sinks)}."
        )
    if len(sentences) > MAX_FLOW_SENTENCES:
        hidden = len(sentences) - MAX_FLOW_SENTENCES
        sentences = [
            *sentences[: MAX_FLOW_SENTENCES - 1],
            f"… ({hidden} more steps)",
            sentences[-1],
        ]
    if not sentences:
        sentences = ["The diagram has no connections to describe."]
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(ctx.graph.nodes))


def _explain_merge(ctx: _Context) -> GraphAnswer:
    merges = [p for p in _relevant_branches(ctx) if p.merge is not None]
    if not merges:
        return GraphAnswer(text="No branches merge in this diagram.", grounding=Grounding())
    sentences, nodes = [], []
    for item in merges:
        nodes += [item.fork, item.merge, *(n for b in item.branches for n in b)]
        described = join([_branch_text(ctx, b) for b in item.branches])
        sentences.append(
            f"The flow splits after {ctx.name(item.fork)} into {described}; these branches "
            f"merge at {ctx.name(item.merge)}."
        )
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded(nodes))


def _topology_summary(ctx: _Context) -> GraphAnswer:
    report = validate_graph(ctx.graph)
    components = ctx.components()
    forks = [n for n in ctx.graph if len(find_successors(ctx.graph, n)) > 1]
    merges = [n for n in ctx.graph if len(find_predecessors(ctx.graph, n)) > 1]
    sentences = [
        f"The diagram has {_plural(len(components), 'node')} and "
        f"{_plural(ctx.graph.number_of_edges(), 'connection')}.",
        f"Inputs: {ctx.names(report.sources)}. Outputs: {ctx.names(report.sinks)}.",
        f"It branches at {ctx.names(forks)} and merges at {ctx.names(merges)}."
        if forks or merges
        else "It has no branches or merges.",
        "It is acyclic." if report.is_dag else f"It has {_plural(len(report.cycles), 'cycle')}.",
    ]
    if report.component_count > 1:
        sentences.append(f"It falls into {report.component_count} disconnected parts.")
    if report.isolated_nodes:
        sentences.append(f"Isolated nodes: {ctx.names(report.isolated_nodes)}.")
    groups = [n for n in ctx.graph if ctx.is_container(n)]
    if groups:
        sentences.append(f"Groups: {ctx.names(groups)}.")
    return GraphAnswer(text=" ".join(sentences), grounding=ctx.grounded([*forks, *merges]))


# --- mixed ----------------------------------------------------------------------------


def _why(ctx: _Context) -> GraphAnswer:
    """The topological half of a "why" question; the reason itself needs the image."""
    if len(ctx.mentioned) >= 2:
        source, target = ctx.mentioned[0], ctx.mentioned[-1]
        if ctx.simple.has_edge(source, target):
            data = next(iter(ctx.graph.get_edge_data(source, target).values()))
            detail = data["relation"].replace("_", " ")
            if data["label"]:
                detail += f", labeled “{data['label']}”"
            text = (
                f"In the graph, {ctx.name(source)} connects directly to "
                f"{ctx.name(target)} ({detail})."
            )
            grounding = ctx.grounded([source, target], [(source, target)])
        else:
            paths = find_paths(ctx.graph, source, target, limit=1)
            if paths:
                text = (
                    f"In the graph, {ctx.name(source)} reaches {ctx.name(target)} via "
                    f"{' → '.join(ctx.name(n) for n in paths[0])}."
                )
                grounding = ctx.grounded(paths[0], list(zip(paths[0], paths[0][1:], strict=False)))
            else:
                text = f"The graph has no path from {ctx.name(source)} to {ctx.name(target)}."
                grounding = ctx.grounded([source, target], [])
        return GraphAnswer(text=text, grounding=grounding, complete=False)
    if ctx.mentioned:
        return _neighbors(ctx).model_copy(update={"complete": False})
    return GraphAnswer(text="", grounding=Grounding(), complete=False)


# --- helpers --------------------------------------------------------------------------


def _relevant_branches(ctx: _Context) -> list:
    found = find_parallel_branches(ctx.graph)
    if ctx.mentioned:
        wanted = set(ctx.mentioned)
        focused = [
            p
            for p in found
            if p.fork in wanted
            or p.merge in wanted
            or any(n in wanted for b in p.branches for n in b)
        ]
        return focused or found
    return found


def _branch_text(ctx: _Context, branch: list[str]) -> str:
    if not branch:
        return "a direct skip connection"
    if len(branch) <= 4:
        return " → ".join(ctx.name(n) for n in branch)
    return f"{ctx.name(branch[0])} → … → {ctx.name(branch[-1])} ({len(branch)} nodes)"


def _depth(ctx: _Context, branch: list[str]) -> int:
    if not branch:
        return 0
    sub = ctx.simple.subgraph(branch)
    return len(nx.dag_longest_path(sub)) if nx.is_directed_acyclic_graph(sub) else len(branch)


def _flow_order(ctx: _Context) -> list[str]:
    if nx.is_directed_acyclic_graph(ctx.simple):
        return list(
            nx.lexicographical_topological_sort(
                ctx.simple, key=lambda n: ctx.graph.nodes[n]["order"]
            )
        )
    return list(ctx.graph.nodes)


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


_HANDLERS: dict[str, Callable[[_Context], GraphAnswer]] = {
    "count_nodes": _count_nodes,
    "count_edges": _count_edges,
    "successors": _successors,
    "predecessors": _predecessors,
    "sources": _sources,
    "sinks": _sinks,
    "neighbors": _neighbors,
    "parallel": _parallel,
    "paths": _paths,
    "fan_out": _fan_out,
    "fan_in": _fan_in,
    "group_members": _group_members,
    "cycles": _cycles,
    "deeper_branch": _deeper_branch,
    "common_successor": _common_successor,
    "longest_path": _longest_path,
    "explain_flow": _explain_flow,
    "explain_merge": _explain_merge,
    "topology_summary": _topology_summary,
    "why": _why,
}
