from pathlib import Path

import pytest

from app.graph import build_graph
from app.qa.engine import route_with_mentions
from app.qa.entities import find_mentions
from app.schemas import DiagramGraph
from evaluation.metrics.matching import match_graphs
from evaluation.metrics.structural_qa import (
    QUESTION_KINDS,
    StructuralQuestion,
    generate_questions,
    score_questions,
)
from evaluation.tests.helpers import graph

EXAMPLES = sorted((Path(__file__).resolve().parents[2] / "examples" / "outputs").glob("*.json"))

# Fork f → {x, y} → merge m → out; f and x inside group g; plus a repeated label.
DIAMOND = graph(
    [
        ("g", "Backbone", "group"),
        ("i", "Input", "input"),
        ("f", "Fork", "module", "g"),
        ("x", "Left", "module", "g"),
        ("y", "Right"),
        ("m", "Merge", "fusion"),
        ("o", "Output", "output"),
        ("r1", "Norm"),
        ("r2", "Norm"),
    ],
    [
        ("i", "f"),
        ("f", "x"),
        ("f", "y"),
        ("x", "m"),
        ("y", "m"),
        ("m", "o"),
        ("o", "r1"),
        ("o", "r2"),
    ],
)


def by_kind(questions: list[StructuralQuestion]) -> dict[str, list[StructuralQuestion]]:
    grouped: dict[str, list[StructuralQuestion]] = {}
    for question in questions:
        grouped.setdefault(question.kind, []).append(question)
    return grouped


def test_questions_cover_every_kind_with_correct_answers() -> None:
    questions = by_kind(generate_questions(DIAMOND, "s1"))

    assert set(questions) == set(QUESTION_KINDS)
    assert questions["sources"][0].answer == ["i"]
    assert questions["sinks"][0].answer == ["r1", "r2"]
    assert questions["count_nodes"][0].answer == 8  # the group is not a node of the flow
    assert questions["count_edges"][0].answer == 8
    assert questions["group_members"][0].entities == ["g"]
    assert questions["group_members"][0].answer == ["f", "x"]
    assert questions["merge_point"][0].entities == ["f"]
    assert questions["merge_point"][0].answer == ["m"]
    reachable, unreachable = questions["path_exists"]
    assert (reachable.answer, unreachable.answer) == (True, False)


def test_questions_avoid_repeated_labels() -> None:
    for seed in range(30):
        for question in generate_questions(DIAMOND, str(seed)):
            assert not {"r1", "r2"} & set(question.entities)


def test_node_questions_answer_with_ground_truth_ids() -> None:
    for seed in range(30):
        for question in generate_questions(DIAMOND, str(seed)):
            if question.kind == "successors" and question.entities == ["f"]:
                assert question.answer == ["x", "y"]
            if question.kind == "predecessors" and question.entities == ["m"]:
                assert question.answer == ["x", "y"]


def test_generation_is_deterministic_per_seed() -> None:
    assert generate_questions(DIAMOND, "a") == generate_questions(DIAMOND, "a")
    variants = {tuple(q.id for q in generate_questions(DIAMOND, str(s))) for s in range(20)}
    assert len(variants) > 1


def test_answers_keep_their_type_through_json() -> None:
    for question in generate_questions(DIAMOND, "s1"):
        again = StructuralQuestion.model_validate_json(question.model_dump_json())
        assert type(again.answer) is type(question.answer)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_ground_truth_answers_all_its_own_questions(path: Path) -> None:
    gt = DiagramGraph.model_validate_json(path.read_text())
    questions = generate_questions(gt, path.stem)

    outcomes = score_questions(questions, gt, match_graphs(gt, gt))

    assert questions and all(o.correct for o in outcomes)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_question_texts_route_to_their_intent(path: Path) -> None:
    gt = DiagramGraph.model_validate_json(path.read_text())
    graph_ = build_graph(gt)

    for question in generate_questions(gt, path.stem):
        route = route_with_mentions(question.text, find_mentions(question.text, gt, graph_))
        assert route.intent == question.intent, question.text


def test_prediction_is_resolved_through_the_matching() -> None:
    # Same structure, different ids, one label misspelled but still matched.
    pred = graph(
        [
            ("G", "Backbone", "group"),
            ("I", "Input", "input"),
            ("F", "Forks", "module", "G"),
            ("X", "Left", "module", "G"),
            ("Y", "Right"),
            ("M", "Merge", "fusion"),
            ("O", "Output", "output"),
            ("R1", "Norm"),
            ("R2", "Norm"),
        ],
        [
            ("I", "F"),
            ("F", "X"),
            ("F", "Y"),
            ("X", "M"),
            ("Y", "M"),
            ("M", "O"),
            ("O", "R1"),
            ("O", "R2"),
        ],
    )
    questions = generate_questions(DIAMOND, "s1")

    outcomes = score_questions(questions, pred, match_graphs(pred, DIAMOND))

    assert all(o.correct for o in outcomes)


def test_a_missing_edge_breaks_only_the_questions_it_affects() -> None:
    pred = graph(
        [(n.id, n.label, n.type, n.group_id) for n in DIAMOND.nodes],
        [(e.source, e.target) for e in DIAMOND.edges if (e.source, e.target) != ("y", "m")],
    )
    questions = [
        q
        for s in range(40)
        for q in generate_questions(DIAMOND, str(s))
        if q.kind in {"merge_point", "count_edges", "sources"}
        or (q.kind == "predecessors" and q.entities == ["m"])
    ]

    outcomes = {o.id: o for o in score_questions(questions, pred, match_graphs(pred, DIAMOND))}

    assert not outcomes["merge_point:f"].correct
    assert outcomes["merge_point:f"].predicted == []
    assert not outcomes["count_edges"].correct and outcomes["count_edges"].predicted == 7
    assert not outcomes["predecessors:m"].correct and outcomes["predecessors:m"].predicted == ["x"]
    assert outcomes["sources"].correct


def test_unmatched_entity_and_unmatched_answer_nodes_are_wrong() -> None:
    pred = graph(
        [("I", "Input", "input"), ("F", "Something else"), ("O", "Output", "output")],
        [("I", "F"), ("F", "O")],
    )
    gt = graph(
        [("i", "Input", "input"), ("f", "Fork"), ("o", "Output", "output")],
        [("i", "f"), ("f", "o")],
    )
    questions = [q for s in range(20) for q in generate_questions(gt, str(s))]

    outcomes = {o.id: o for o in score_questions(questions, pred, match_graphs(pred, gt))}

    assert outcomes["successors:f"].predicted is None and not outcomes["successors:f"].correct
    assert outcomes["successors:i"].predicted == ["<unmatched:F>"]
    assert not outcomes["successors:i"].correct
    assert outcomes["count_nodes"].correct  # three nodes either way


def test_failed_prediction_answers_everything_wrong() -> None:
    questions = generate_questions(DIAMOND, "s1")

    outcomes = score_questions(questions, None, None)

    assert len(outcomes) == len(questions)
    assert not any(o.correct for o in outcomes)


def test_a_count_of_one_never_equals_true() -> None:
    single_edge = graph([("a", "Alpha"), ("b", "Bravo")], [("a", "b")])
    questions = [q for q in generate_questions(single_edge, "x") if q.kind == "count_edges"]
    forged = [q.model_copy(update={"answer": True}) for q in questions]

    outcomes = score_questions(forged, single_edge, match_graphs(single_edge, single_edge))

    assert outcomes[0].predicted == 1 and not outcomes[0].correct
