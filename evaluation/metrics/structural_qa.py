"""Structural QA accuracy (spec §20.7): questions generated from the ground truth, answered
on the predicted graph.

``QA_BENCHMARK_VERSION`` pins question generation and scoring; changing either is a
versioned decision (bump it, record why in CLAUDE.md).

Definition, QA benchmark v1:

- Questions are generated per ground-truth graph, deterministically from a seed string
  (the sample id), and only about nodes whose label is unique in the ground truth — a
  question about one of three "Conv 3x3" blocks has no single right answer. Per graph, at
  most one question of each kind where the graph has a suitable node:
  ``successors`` / ``predecessors`` of a node, ``sources``, ``sinks``, ``path_exists``
  (one reachable pair, preferring pairs at distance ≥ 2, and one unreachable pair),
  ``count_nodes`` (non-group nodes), ``count_edges``, ``group_members`` (direct members of
  a group) and ``merge_point`` (where the parallel branches leaving a fork merge).
- Answers are computed with the topology functions the QA engine uses
  (``app.graph``), on the ground truth for the expected answer and on the prediction for
  the predicted one.
- Entities are resolved in the prediction through the §20.1 assignment, and predicted
  answer nodes are mapped back through it. This scores the *structure* the prediction
  supports; misread labels are measured by label accuracy instead. A question whose
  entity has no matched predicted node is answered wrong.
- An answer is correct when it equals the expected one exactly: the same set of
  ground-truth nodes (an unmatched predicted node never equals one), the same boolean,
  the same count. A failed prediction (no graph) answers every question wrong.
- Each question carries a natural-language ``text`` in the phrasing the QA router maps to
  ``intent``, so the same questions can later drive an end-to-end QA evaluation.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Callable
from typing import Literal

import networkx as nx
from pydantic import BaseModel

from app.graph import (
    build_graph,
    find_group_members,
    find_parallel_branches,
    find_predecessors,
    find_sinks,
    find_sources,
    find_successors,
)
from app.schemas import DiagramGraph
from evaluation.metrics.matching import MatchResult, matching_label

QA_BENCHMARK_VERSION = "1"

QuestionKind = Literal[
    "successors",
    "predecessors",
    "sources",
    "sinks",
    "path_exists",
    "count_nodes",
    "count_edges",
    "group_members",
    "merge_point",
]
QUESTION_KINDS: tuple[QuestionKind, ...] = QuestionKind.__args__

Answer = list[str] | bool | int


class StructuralQuestion(BaseModel):
    id: str
    kind: QuestionKind
    text: str
    intent: str  # the QA router intent ``text`` is phrased for
    entities: list[str]  # ground-truth node ids
    answer: Answer  # expected; node answers are sorted ground-truth ids


class QuestionOutcome(BaseModel):
    id: str
    kind: QuestionKind
    correct: bool
    predicted: Answer | None  # None: an entity was not matched, or no graph


def generate_questions(ground_truth: DiagramGraph, seed: str) -> list[StructuralQuestion]:
    rng = random.Random(f"structural-qa:{QA_BENCHMARK_VERSION}:{seed}")
    graph = build_graph(ground_truth)
    simple = nx.DiGraph(graph)
    counts = Counter(matching_label(n.label) for n in ground_truth.nodes)
    unique = [n.id for n in ground_truth.nodes if counts[matching_label(n.label)] == 1]
    components = [n for n in unique if graph.nodes[n]["type"] != "group"]
    label = {n.id: n.label for n in ground_truth.nodes}
    questions: list[StructuralQuestion] = []

    def add(kind: QuestionKind, text: str, intent: str, entities: list[str]) -> None:
        question = StructuralQuestion(
            id=":".join([kind, *entities]),
            kind=kind,
            text=text,
            intent=intent,
            entities=entities,
            answer=0,
        )
        identity = {n: n for n in label}
        answer = answer_question(question, ground_truth, identity, identity)
        questions.append(question.model_copy(update={"answer": answer}))

    def pick(candidates: list[str]) -> str | None:
        return rng.choice(candidates) if candidates else None

    if node := pick([n for n in components if simple.out_degree(n) > 0]):
        add("successors", f"What comes after {label[node]}?", "successors", [node])
    if node := pick([n for n in components if simple.in_degree(n) > 0]):
        add("predecessors", f"What feeds into {label[node]}?", "predecessors", [node])
    add("sources", "What are the inputs of the diagram?", "sources", [])
    add("sinks", "What are the final outputs of the diagram?", "sinks", [])

    reachable = {n: nx.descendants(simple, n) for n in components}
    pairs = [(a, b) for a in components for b in components if a != b and b in reachable[a]]
    far = [(a, b) for a, b in pairs if not simple.has_edge(a, b)]
    if pair := (rng.choice(far or pairs) if pairs else None):
        add("path_exists", _path_text(label, *pair), "paths", list(pair))
    unreachable = [
        (a, b) for a in components for b in components if a != b and b not in reachable[a]
    ]
    if pair := (rng.choice(unreachable) if unreachable else None):
        add("path_exists", _path_text(label, *pair), "paths", list(pair))

    add("count_nodes", "How many nodes does the diagram have?", "count_nodes", [])
    add("count_edges", "How many connections are there?", "count_edges", [])

    groups = [n for n in unique if graph.nodes[n]["type"] == "group"]
    if node := pick([g for g in groups if find_group_members(graph, g)]):
        add("group_members", f"What is inside {label[node]}?", "group_members", [node])
    forks = sorted(
        {b.fork for b in find_parallel_branches(graph) if b.merge is not None} & set(components)
    )
    if node := pick(forks):
        add(
            "merge_point",
            f"Where do the branches from {label[node]} merge?",
            "common_successor",
            [node],
        )
    return questions


def _path_text(label: dict[str, str], a: str, b: str) -> str:
    return f"Is there a path from {label[a]} to {label[b]}?"


def answer_question(
    question: StructuralQuestion,
    graph_diagram: DiagramGraph,
    to_graph: dict[str, str],
    to_ground_truth: Callable[[str], str] | dict[str, str],
) -> Answer | None:
    """Answer ``question`` on ``graph_diagram``.

    ``to_graph`` maps ground-truth entity ids to this graph's ids; ``to_ground_truth`` maps
    this graph's ids back (answers are expressed in ground-truth ids). Returns None when an
    entity has no counterpart in this graph.
    """
    if any(entity not in to_graph for entity in question.entities):
        return None
    entities = [to_graph[entity] for entity in question.entities]
    graph = build_graph(graph_diagram)
    back = to_ground_truth.__getitem__ if isinstance(to_ground_truth, dict) else to_ground_truth

    def nodes(ids: list[str]) -> list[str]:
        return sorted({back(n) for n in ids})

    match question.kind:
        case "successors":
            return nodes(find_successors(graph, entities[0]))
        case "predecessors":
            return nodes(find_predecessors(graph, entities[0]))
        case "sources":
            return nodes(find_sources(graph))
        case "sinks":
            return nodes(find_sinks(graph))
        case "path_exists":
            return nx.has_path(graph, entities[0], entities[1])
        case "count_nodes":
            return sum(data["type"] != "group" for _, data in graph.nodes(data=True))
        case "count_edges":
            return graph.number_of_edges()
        case "group_members":
            return nodes(find_group_members(graph, entities[0]))
        case "merge_point":
            return nodes(
                [
                    b.merge
                    for b in find_parallel_branches(graph)
                    if b.fork == entities[0] and b.merge is not None
                ]
            )


def score_questions(
    questions: list[StructuralQuestion],
    predicted: DiagramGraph | None,
    match: MatchResult | None,
) -> list[QuestionOutcome]:
    if predicted is None or match is None:
        return [
            QuestionOutcome(id=q.id, kind=q.kind, correct=False, predicted=None) for q in questions
        ]
    to_predicted = {pair.ground_truth: pair.predicted for pair in match.node_pairs}
    assignment = match.assignment

    def to_ground_truth(node_id: str) -> str:
        return assignment.get(node_id, f"<unmatched:{node_id}>")

    outcomes = []
    for question in questions:
        answer = answer_question(question, predicted, to_predicted, to_ground_truth)
        correct = answer is not None and _same(answer, question.answer)
        outcomes.append(
            QuestionOutcome(id=question.id, kind=question.kind, correct=correct, predicted=answer)
        )
    return outcomes


def _same(a: Answer, b: Answer) -> bool:
    # bool is an int subclass: never let True equal a count of 1.
    return type(a) is type(b) and a == b
