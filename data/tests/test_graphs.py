import random
from collections import Counter

import pytest

from app.graph import build_graph, find_parallel_branches
from app.schemas import DiagramGraph
from data.generator.graphs import DIAGRAM_TYPES, LEVELS, generate_graph

SAMPLES = 40


def generated(level: int, diagram_type: str, count: int = SAMPLES):
    return [
        generate_graph(random.Random(f"{level}/{diagram_type}/{seed}"), level, diagram_type)
        for seed in range(count)
    ]


@pytest.mark.parametrize("level", sorted(LEVELS))
@pytest.mark.parametrize("diagram_type", DIAGRAM_TYPES)
def test_graphs_are_valid_and_sized_for_their_level(level: int, diagram_type: str) -> None:
    low, high = LEVELS[level]
    for sample in generated(level, diagram_type):
        DiagramGraph.model_validate(sample.graph.model_dump())  # round-trips the schema
        assert low <= sample.spec.n_nodes <= high
        assert sample.spec.diagram_type == diagram_type
        assert sample.spec.n_edges == len(sample.graph.edges)
        assert all(node.label.strip() for node in sample.graph.nodes)


def test_generation_is_deterministic_per_seed() -> None:
    first = generate_graph(random.Random(42), 3, "flowchart")
    second = generate_graph(random.Random(42), 3, "flowchart")
    other = generate_graph(random.Random(43), 3, "flowchart")

    assert (first.graph, first.spec) == (second.graph, second.spec)
    assert first.graph != other.graph


@pytest.mark.parametrize("level", [1, 2])
def test_low_levels_are_simple(level: int) -> None:
    for diagram_type in DIAGRAM_TYPES:
        for sample in generated(level, diagram_type):
            assert not sample.spec.has_cycle
            assert "long_range" not in sample.spec.patterns
            assert sample.spec.group_depth <= (0 if level == 1 else 1)


def test_harder_levels_contain_the_harder_patterns() -> None:
    patterns = Counter(
        p
        for level in (3, 4)
        for diagram_type in DIAGRAM_TYPES
        for sample in generated(level, diagram_type, 20)
        for p in sample.spec.patterns
    )

    for pattern in (
        "cycle",
        "long_range",
        "nested",
        "nested_deep",
        "multi_branch",
        "fan_in",
        "residual",
        "skip",
        "decision",
        "labeled_edges",
        "repeated_labels",
    ):
        assert patterns[pattern] > 0, pattern


def test_complexity_grows_with_level() -> None:
    def mean(level: int, attribute: str) -> float:
        specs = [s.spec for t in DIAGRAM_TYPES for s in generated(level, t, 15)]
        return sum(getattr(s, attribute) for s in specs) / len(specs)

    for attribute in ("n_nodes", "n_edges", "depth", "n_groups"):
        values = [mean(level, attribute) for level in sorted(LEVELS)]
        assert values == sorted(values), attribute


def test_recorded_patterns_match_the_graph() -> None:
    for level in (2, 3, 4):
        for diagram_type in ("neural_network", "flowchart", "data_pipeline"):
            for sample in generated(level, diagram_type, 15):
                spec, graph = sample.spec, sample.graph
                assert ("cycle" in spec.patterns) == spec.has_cycle
                if "nested" in spec.patterns:
                    assert spec.n_groups >= 1
                if "nested_deep" in spec.patterns:
                    assert spec.group_depth == 2
                if "decision" in spec.patterns:
                    labels = {e.label for e in graph.edges}
                    assert {"Yes", "No"} <= labels
                if {"branching", "merging"} <= set(spec.patterns) and not spec.has_cycle:
                    assert find_parallel_branches(build_graph(graph))


def test_decision_branches_are_labeled_yes_and_no() -> None:
    sample = next(s for s in generated(2, "flowchart", 60) if "decision" in s.spec.patterns)
    decisions = {n.id for n in sample.graph.nodes if n.type.value == "decision"}
    outgoing = [e.label for e in sample.graph.edges if e.source in decisions]

    assert sorted(outgoing)[:2] == ["No", "Yes"]


def test_uml_uses_uml_relations_and_class_names() -> None:
    relations = Counter(e.relation.value for s in generated(3, "uml") for e in s.graph.edges)

    assert set(relations) <= {"inherits_from", "composes", "aggregates", "depends_on"}
    assert relations["inherits_from"] > 0


def test_repeated_labels_occur_only_in_neural_networks() -> None:
    for diagram_type in DIAGRAM_TYPES:
        repeated = any("repeated_labels" in s.spec.patterns for s in generated(3, diagram_type))
        assert repeated == (diagram_type == "neural_network"), diagram_type


def test_unknown_level_or_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="level"):
        generate_graph(random.Random(0), 5, "flowchart")
    with pytest.raises(ValueError, match="diagram type"):
        generate_graph(random.Random(0), 1, "mind_map")
