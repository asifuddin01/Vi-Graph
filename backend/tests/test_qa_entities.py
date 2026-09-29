from pathlib import Path

from app.graph import build_graph
from app.qa.entities import find_mentions, unique_nodes
from app.schemas import DiagramGraph

FIXTURES = Path(__file__).parent / "fixtures"


def spec() -> DiagramGraph:
    return DiagramGraph.model_validate_json((FIXTURES / "graph_v2_example.json").read_text())


def labeled(*labels: str) -> DiagramGraph:
    return DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": "flowchart",
            "nodes": [
                {"id": f"n{i}", "label": label, "type": "module"}
                for i, label in enumerate(labels, start=1)
            ],
            "edges": [],
        }
    )


def mentions(question: str, diagram: DiagramGraph) -> list[tuple[str, str]]:
    return [(m.node_id, m.how) for m in find_mentions(question, diagram, build_graph(diagram))]


def test_exact_mentions_come_back_in_question_order() -> None:
    found = mentions("Paths from classifier back to INPUT  image?", spec())

    assert found == [("n5", "exact"), ("n1", "exact")]


def test_longest_label_wins_an_overlap() -> None:
    diagram = labeled("Encoder", "Transformer Encoder")

    assert mentions("What follows the Transformer Encoder?", diagram) == [("n2", "exact")]
    assert mentions("What follows the Encoder?", diagram) == [("n1", "exact")]


def test_mentions_respect_word_boundaries() -> None:
    assert mentions("What is the ReLUx layer?", labeled("ReLU")) == []
    assert mentions("What do the Transformers do?", labeled("Transform")) == []


def test_fuzzy_mention_of_a_misspelled_label() -> None:
    assert mentions("What comes after the Clasifier?", spec()) == [("n5", "fuzzy")]


def test_punctuation_variants_match_fuzzily() -> None:
    assert mentions("where is multi head attention used", labeled("Multi-Head Attention")) == [
        ("n1", "fuzzy")
    ]


def test_short_labels_are_never_fuzzy_matched() -> None:
    assert mentions("what does the addd do", labeled("Add")) == []


def test_node_ids_can_be_mentioned() -> None:
    assert mentions("what comes after n3?", spec()) == [("n3", "id")]


def test_repeated_labels_return_every_matching_node() -> None:
    diagram = labeled("Conv 3x3", "ReLU", "Conv 3x3")

    assert unique_nodes(find_mentions("after conv 3x3?", diagram, build_graph(diagram))) == [
        "n1",
        "n3",
    ]


def test_generic_input_and_output_resolve_to_sources_and_sinks() -> None:
    assert mentions("What comes after the input?", spec()) == [("n1", "generic")]
    assert mentions("What feeds the final output?", spec()) == [("n5", "generic")]


def test_generic_words_do_not_override_named_nodes() -> None:
    assert mentions("What does the output of CNN Encoder feed?", spec()) == [("n2", "exact")]


def test_no_mentions() -> None:
    assert mentions("What comes after it?", spec()) == []
