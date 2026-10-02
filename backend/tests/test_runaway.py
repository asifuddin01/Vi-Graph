import json
import random

import pytest

from app.vlm.runaway import RunawayGuard, label_template
from data.generator.dataset import default_config, sample_graph

GUARD = RunawayGuard()


def nodes_json(labels: list[str]) -> str:
    nodes = ",".join(
        f'{{"id":"n{i}","label":"{label}","type":"module"}}' for i, label in enumerate(labels, 1)
    )
    return f'{{"schema_version":"2.0","diagram_type":"other","nodes":[{nodes}'


def with_edges(labels: list[str], edges: list[tuple[str, str]]) -> str:
    listed = ",".join(f'{{"source":"{s}","target":"{t}","relation":"flows_to"}}' for s, t in edges)
    return nodes_json(labels) + f'],"edges":[{listed}'


def test_label_template_replaces_numbers() -> None:
    assert label_template("  Shard   65 ") == label_template("shard 7") == "shard #"
    assert label_template("Conv 5x5") == "conv #x#"
    assert label_template("Dropout 0.25") == "dropout #"


def test_node_loop_needs_both_a_long_list_and_few_templates() -> None:
    counting = [f"Shard {i}" for i in range(1, 60)]
    varied = [f"Block {chr(65 + i % 26)}{i}" if i % 3 else f"Shard {i}" for i in range(60)]

    assert GUARD.check(nodes_json(counting[:49])) is None  # e.g. a long ResNet: allowed
    assert GUARD.check(nodes_json(counting[:50])).startswith("node loop: 50 nodes")
    assert GUARD.check(nodes_json(varied)) is None


def test_node_loop_catches_alternating_labels() -> None:
    labels = [f"Layer {i}" for i in range(40)] + ["Dropout 0.2", "Conv 5x5"] * 6

    assert "2 label template(s)" in GUARD.check(nodes_json(labels))


def test_edges_to_undeclared_nodes() -> None:
    labels = [f"Step {chr(65 + i)}" for i in range(10)]
    chain = [(f"n{i}", f"n{i + 1}") for i in range(1, 10)]
    beyond = chain + [(f"n{i}", f"n{i + 1}") for i in range(10, 17)]  # 7 point past n10

    assert GUARD.check(with_edges(labels, beyond)) is None
    beyond.append(("n17", "n18"))  # the 8th in a row
    assert GUARD.check(with_edges(labels, beyond)).startswith("undeclared edges")


def test_edge_loop_but_not_edges_listed_twice() -> None:
    labels = [f"Step {chr(65 + i)}" for i in range(10)]
    twice = [pair for i in range(1, 10) for pair in [(f"n{i}", f"n{i + 1}")] * 2]
    cycling = [("n1", "n2")] + [("n4", "n9"), ("n5", "n9"), ("n6", "n9")] * 4

    assert GUARD.check(with_edges(labels, twice)) is None  # duplicates: Stage D removes them
    assert GUARD.check(with_edges(labels, cycling)).startswith("edge loop")


def test_numeric_ids_and_pretty_printed_json() -> None:
    text = json.dumps(
        {
            "nodes": [{"id": i, "label": f"Step {chr(65 + i)}"} for i in range(5)],
            "edges": [{"source": 1, "target": 100 + i} for i in range(8)],
        },
        indent=2,
    )

    assert GUARD.check(text[: text.rindex("}")]).startswith("undeclared edges")


@pytest.mark.parametrize("indent", [None, 2])
def test_never_fires_on_ground_truth(indent: int | None) -> None:
    """Every synthetic-v1 train/val graph, compact or indented, at every object boundary of a
    sample of them: the guard must stay silent (thresholds were chosen from this data)."""
    config = default_config()
    checked = random.Random(0)
    for split in config.splits:
        if split.name not in ("train", "val"):
            continue
        for index in range(split.size):
            graph = sample_graph(config, split, index).graph
            text = graph.model_dump_json(exclude_none=True, indent=indent)
            assert GUARD.check(text) is None, f"{split.name}-{index}"
            if checked.random() < 0.02:
                for end in (k + 1 for k, ch in enumerate(text) if ch == "}"):
                    assert GUARD.check(text[:end]) is None, f"{split.name}-{index} at {end}"
