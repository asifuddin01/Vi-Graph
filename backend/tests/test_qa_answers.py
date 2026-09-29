from pathlib import Path

import pytest

from app.graph import build_graph
from app.qa.answers import GraphAnswer, answer_from_graph, join
from app.qa.entities import find_mentions
from app.qa.router import route_question
from app.schemas import DiagramGraph

FIXTURES = Path(__file__).parent / "fixtures"


def spec() -> DiagramGraph:
    return DiagramGraph.model_validate_json((FIXTURES / "graph_v2_example.json").read_text())


def diagram(nodes: list[tuple], edges: list[tuple]) -> DiagramGraph:
    """nodes: (id, label[, type[, group_id]]); edges: (source, target[, relation[, label]])."""
    return DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": "neural_network",
            "nodes": [
                {
                    "id": n[0],
                    "label": n[1],
                    "type": n[2] if len(n) > 2 else "module",
                    "group_id": n[3] if len(n) > 3 else None,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e[0],
                    "target": e[1],
                    "relation": e[2] if len(e) > 2 else "flows_to",
                    "label": e[3] if len(e) > 3 else None,
                }
                for e in edges
            ],
        }
    )


def ask(question: str, graph: DiagramGraph | None = None) -> GraphAnswer:
    graph = graph or spec()
    nx_graph = build_graph(graph)
    answer = answer_from_graph(
        route_question(question).intent, graph, nx_graph, find_mentions(question, graph, nx_graph)
    )
    assert answer is not None
    return answer


# --- golden answers on the spec §7 example (§12.2 questions) --------------------------

GOLDEN = [
    ("What comes after the CNN Encoder?", "After CNN Encoder, the flow goes to Feature Fusion."),
    ("What is the final output?", "The final output is Classifier."),
    (
        "How many nodes are present?",
        "The diagram has 5 nodes: 1 input, 2 modules, 1 fusion node and 1 output.",
    ),
    (
        "Which nodes are connected directly to Feature Fusion?",
        "Feature Fusion receives input from CNN Encoder and Transformer Encoder and sends "
        "output to Classifier.",
    ),
    (
        "Which branches operate in parallel?",
        "After Input Image, CNN Encoder and Transformer Encoder run in parallel and merge at "
        "Feature Fusion.",
    ),
    (
        "What are all paths from Input Image to Classifier?",
        "There are 2 paths from Input Image to Classifier: Input Image → CNN Encoder → Feature "
        "Fusion → Classifier; Input Image → Transformer Encoder → Feature Fusion → Classifier.",
    ),
    (
        "Which nodes have multiple outgoing edges?",
        "Nodes with multiple outgoing edges: Input Image (to CNN Encoder and Transformer Encoder).",
    ),
    (
        "Which branch is deeper?",
        "The branches from Input Image to Feature Fusion are equally deep (1 step each).",
    ),
    (
        "Which component receives outputs from both branches?",
        "Feature Fusion receives the outputs of the branches from Input Image: CNN Encoder and "
        "Transformer Encoder.",
    ),
    (
        "Explain the data flow from input to output.",
        "The diagram starts at Input Image. Input Image branches into CNN Encoder and "
        "Transformer Encoder. CNN Encoder and Transformer Encoder are combined at Feature "
        "Fusion. Feature Fusion feeds Classifier. The final output is Classifier.",
    ),
    (
        "Explain where the branches merge.",
        "The flow splits after Input Image into CNN Encoder and Transformer Encoder; these "
        "branches merge at Feature Fusion.",
    ),
    (
        "Analyze the topology",
        "The diagram has 5 nodes and 5 connections. Inputs: Input Image. Outputs: Classifier. "
        "It branches at Input Image and merges at Feature Fusion. It is acyclic.",
    ),
]


@pytest.mark.parametrize(("question", "expected"), GOLDEN)
def test_golden_answers(question: str, expected: str) -> None:
    assert ask(question).text == expected


def test_answers_are_grounded_in_nodes_and_edges() -> None:
    answer = ask("What comes after the input?")

    assert answer.grounding.nodes == ["n1", "n2", "n3"]
    assert answer.grounding.edges == [("n1", "n2"), ("n1", "n3")]


def test_parallel_answer_grounds_the_whole_diamond() -> None:
    grounding = ask("Which branches operate in parallel?").grounding

    assert sorted(grounding.nodes) == ["n1", "n2", "n3", "n4"]
    assert sorted(grounding.edges) == [("n1", "n2"), ("n1", "n3"), ("n2", "n4"), ("n3", "n4")]


def test_a_node_question_without_a_node_asks_which_one() -> None:
    answer = ask("What comes after it?")

    assert answer.text.startswith("I couldn't tell which node you mean. The nodes are: Input Image")
    assert answer.grounding.nodes == []


# --- other shapes of graph ------------------------------------------------------------

RESNET = diagram(
    [
        ("x", "Input"),
        ("c1", "Conv 3x3"),
        ("r", "ReLU", "operation"),
        ("c2", "Conv 3x3"),
        ("add", "Addition", "fusion"),
        ("out", "Output", "output"),
    ],
    [
        ("x", "c1"),
        ("c1", "r"),
        ("r", "c2"),
        ("c2", "add"),
        ("x", "add", "flows_to", "skip"),
        ("add", "out"),
    ],
)


def test_skip_connection_is_described() -> None:
    assert ask("Which branches operate in parallel?", RESNET).text == (
        "After Input, Conv 3x3 (c1) → ReLU → Conv 3x3 (c2) and a direct skip connection run in "
        "parallel and merge at Addition."
    )


def test_deeper_branch_is_named() -> None:
    assert ask("Which branch is deeper?", RESNET).text == (
        "Of the branches from Input to Addition, the one through Conv 3x3 (c1) → ReLU → "
        "Conv 3x3 (c2) is deeper (3 steps) than a direct skip connection (0 steps)."
    )


def test_repeated_labels_are_answered_for_each_node() -> None:
    assert ask("What comes after Conv 3x3?", RESNET).text == (
        "After Conv 3x3 (c1), the flow goes to ReLU. After Conv 3x3 (c2), the flow goes to "
        "Addition."
    )


def test_why_gives_the_graph_part_and_is_incomplete() -> None:
    answer = ask("Why does the Input connect to Addition?", RESNET)

    assert (
        answer.text
        == "In the graph, Input connects directly to Addition (flows to, labeled “skip”)."
    )
    assert answer.complete is False
    assert answer.grounding.edges == [("x", "add")]


def test_why_without_a_direct_edge_describes_the_path() -> None:
    answer = ask("Why does ReLU lead to Output?", RESNET)

    assert (
        answer.text
        == "In the graph, ReLU reaches Output via ReLU → Conv 3x3 (c2) → Addition → Output."
    )


CYCLIC = diagram(
    [
        ("a", "Start", "input"),
        ("b", "Check", "decision"),
        ("c", "Retry", "operation"),
        ("d", "Done", "output"),
    ],
    [("a", "b"), ("b", "c", "branches_to", "No"), ("c", "b"), ("b", "d", "branches_to", "Yes")],
)


def test_cycles_are_reported() -> None:
    answer = ask("Is there a feedback loop?", CYCLIC)

    assert answer.text == "The graph has 1 cycle: Check → Retry → Check."
    assert answer.grounding.edges == [("b", "c"), ("c", "b")]


def test_longest_path_is_undefined_with_cycles() -> None:
    assert "no well-defined longest path" in ask("What is the longest path?", CYCLIC).text


def test_flow_explanation_mentions_cycles() -> None:
    assert "The flow contains cycles." in ask("Explain the flow", CYCLIC).text


GROUPED = diagram(
    [
        ("blk", "Encoder Block", "group"),
        ("att", "Attention", "module", "blk"),
        ("ffn", "Feed Forward", "module", "blk"),
        ("head", "Head", "output"),
    ],
    [("att", "ffn"), ("ffn", "head")],
)


def test_group_members() -> None:
    assert ask("What is inside the Encoder Block?", GROUPED).text == (
        "Encoder Block contains Attention and Feed Forward."
    )


def test_asking_for_members_of_a_non_group() -> None:
    assert ask("What does Attention contain?", GROUPED).text == (
        "Attention is not a group; it is inside Encoder Block."
    )


def test_node_count_mentions_groups() -> None:
    assert ask("How many nodes are there?", GROUPED).text == (
        "The diagram has 3 nodes: 2 modules and 1 output. They are organized in 1 group "
        "(Encoder Block)."
    )


def test_linear_graph_has_no_parallel_branches() -> None:
    linear = diagram([("a", "A"), ("b", "B")], [("a", "b")])

    assert ask("Which branches run in parallel?", linear).text == (
        "There are no parallel branches; the flow is linear."
    )


@pytest.mark.parametrize(
    ("items", "joined"),
    [([], "nothing"), (["A"], "A"), (["A", "B"], "A and B"), (["A", "B", "C"], "A, B and C")],
)
def test_join(items: list[str], joined: str) -> None:
    assert join(items) == joined


def test_unhandled_intent_returns_none() -> None:
    graph = spec()

    assert answer_from_graph("describe_visual", graph, build_graph(graph), []) is None
