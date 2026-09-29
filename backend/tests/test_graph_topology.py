from pathlib import Path

import pytest

from app.graph import (
    ParallelBranches,
    build_graph,
    find_group_members,
    find_parallel_branches,
    find_paths,
    find_predecessors,
    find_sinks,
    find_sources,
    find_successors,
    flatten_groups,
    validate_graph,
)
from app.schemas import DiagramGraph

FIXTURES = Path(__file__).parent / "fixtures"


def spec_example() -> DiagramGraph:
    return DiagramGraph.model_validate_json((FIXTURES / "graph_v2_example.json").read_text())


def diagram(nodes: list[tuple], edges: list[tuple] = ()) -> DiagramGraph:
    """nodes: (id[, type[, group_id]]); edges: (source, target[, relation[, label]])."""
    return DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": "flowchart",
            "nodes": [
                {
                    "id": n[0],
                    "label": n[0].upper(),
                    "type": n[1] if len(n) > 1 else "module",
                    "group_id": n[2] if len(n) > 2 else None,
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


# --- build_graph ----------------------------------------------------------------------


def test_build_graph_keeps_attributes_and_order() -> None:
    graph = build_graph(spec_example())

    assert list(graph.nodes) == ["n1", "n2", "n3", "n4", "n5"]
    assert graph.nodes["n4"] == {
        "label": "Feature Fusion",
        "type": "fusion",
        "group_id": None,
        "bbox": None,
        "confidence": None,
        "order": 3,
    }
    assert graph.graph == {"schema_version": "2.0", "diagram_type": "neural_network"}
    assert graph.number_of_edges() == 5


def test_parallel_edges_are_preserved() -> None:
    graph = build_graph(
        diagram(
            [("d", "decision"), ("x",)],
            [("d", "x", "branches_to", "Yes"), ("d", "x", "branches_to", "No")],
        )
    )

    assert graph.number_of_edges("d", "x") == 2
    assert sorted(data["label"] for _, _, data in graph.edges(data=True)) == ["No", "Yes"]


# --- neighbours, sources, sinks, paths ------------------------------------------------


def test_neighbours_of_the_spec_example() -> None:
    graph = build_graph(spec_example())

    assert find_successors(graph, "n1") == ["n2", "n3"]
    assert find_predecessors(graph, "n4") == ["n2", "n3"]
    assert find_predecessors(graph, "n1") == []
    assert find_sources(graph) == ["n1"]
    assert find_sinks(graph) == ["n5"]


def test_neighbours_are_deduplicated_across_parallel_edges() -> None:
    graph = build_graph(diagram([("a",), ("b",)], [("a", "b"), ("a", "b", "depends_on")]))

    assert find_successors(graph, "a") == ["b"]


def test_unknown_node_raises() -> None:
    with pytest.raises(KeyError, match="unknown node id 'zz'"):
        find_successors(build_graph(spec_example()), "zz")


def test_all_paths_shortest_first() -> None:
    graph = build_graph(spec_example())

    assert find_paths(graph, "n1", "n5") == [["n1", "n2", "n4", "n5"], ["n1", "n3", "n4", "n5"]]
    assert find_paths(graph, "n5", "n1") == []


def test_path_count_is_limited() -> None:
    # A ladder of 8 diamonds has 2**8 = 256 paths.
    nodes = (
        [(f"v{i}",) for i in range(9)]
        + [(f"a{i}",) for i in range(8)]
        + [(f"b{i}",) for i in range(8)]
    )
    edges = [
        e
        for i in range(8)
        for e in [
            (f"v{i}", f"a{i}"),
            (f"v{i}", f"b{i}"),
            (f"a{i}", f"v{i + 1}"),
            (f"b{i}", f"v{i + 1}"),
        ]
    ]

    assert len(find_paths(build_graph(diagram(nodes, edges)), "v0", "v8", limit=10)) == 10


def test_pure_group_containers_are_neither_sources_nor_sinks() -> None:
    graph = build_graph(
        diagram([("g", "group"), ("a", "module", "g"), ("b", "module", "g")], [("a", "b")])
    )

    assert find_sources(graph) == ["a"]
    assert find_sinks(graph) == ["b"]


# --- parallel branches ----------------------------------------------------------------


def test_spec_example_branches_run_in_parallel_until_fusion() -> None:
    assert find_parallel_branches(build_graph(spec_example())) == [
        ParallelBranches(fork="n1", merge="n4", branches=[["n2"], ["n3"]])
    ]


def test_skip_connection_is_an_empty_branch() -> None:
    graph = build_graph(
        diagram(
            [("x",), ("conv1",), ("relu",), ("conv2",), ("add", "fusion"), ("out",)],
            [
                ("x", "conv1"),
                ("conv1", "relu"),
                ("relu", "conv2"),
                ("conv2", "add"),
                ("x", "add"),
                ("add", "out"),
            ],
        )
    )

    assert find_parallel_branches(graph) == [
        ParallelBranches(fork="x", merge="add", branches=[["conv1", "relu", "conv2"], []])
    ]


def test_branch_nodes_follow_flow_order_not_listing_order() -> None:
    graph = build_graph(
        diagram(
            [("in",), ("late",), ("early",), ("other",), ("join",)],
            [
                ("in", "early"),
                ("early", "late"),
                ("late", "join"),
                ("in", "other"),
                ("other", "join"),
            ],
        )
    )

    assert find_parallel_branches(graph)[0].branches == [["early", "late"], ["other"]]


def test_fork_that_never_merges() -> None:
    graph = build_graph(
        diagram([("in",), ("a",), ("a2",), ("b",)], [("in", "a"), ("a", "a2"), ("in", "b")])
    )

    assert find_parallel_branches(graph) == [
        ParallelBranches(fork="in", merge=None, branches=[["a", "a2"], ["b"]])
    ]


def test_three_way_fork_and_nested_fork() -> None:
    graph = build_graph(
        diagram(
            [("in",), ("a",), ("b",), ("c",), ("b1",), ("b2",), ("bj",), ("join",)],
            [
                ("in", "a"),
                ("in", "b"),
                ("in", "c"),
                ("a", "join"),
                ("c", "join"),
                ("b", "b1"),
                ("b", "b2"),
                ("b1", "bj"),
                ("b2", "bj"),
                ("bj", "join"),
            ],
        )
    )

    assert find_parallel_branches(graph) == [
        ParallelBranches(fork="in", merge="join", branches=[["a"], ["b", "b1", "b2", "bj"], ["c"]]),
        ParallelBranches(fork="b", merge="bj", branches=[["b1"], ["b2"]]),
    ]


def test_linear_graph_has_no_parallel_branches() -> None:
    graph = build_graph(diagram([("a",), ("b",), ("c",)], [("a", "b"), ("b", "c")]))

    assert find_parallel_branches(graph) == []


# --- groups ---------------------------------------------------------------------------


def nested() -> DiagramGraph:
    return diagram(
        [
            ("block", "group"),
            ("inner", "group", "block"),
            ("conv", "module", "inner"),
            ("bn", "operation", "inner"),
            ("relu", "operation", "block"),
            ("head",),
        ],
        [("conv", "bn"), ("bn", "relu"), ("relu", "head")],
    )


def test_direct_and_recursive_group_members() -> None:
    graph = build_graph(nested())

    assert find_group_members(graph, "block") == ["inner", "relu"]
    assert find_group_members(graph, "block", recursive=True) == ["inner", "conv", "bn", "relu"]
    assert find_group_members(graph, "head") == []


def test_flatten_groups_removes_nesting_and_pure_containers() -> None:
    flat = flatten_groups(nested())

    assert [n.id for n in flat.nodes] == ["conv", "bn", "relu", "head"]
    assert all(n.group_id is None for n in flat.nodes)
    assert flat.edges == nested().edges


def test_flatten_keeps_group_nodes_that_are_edge_endpoints() -> None:
    flat = flatten_groups(diagram([("g", "group"), ("a", "module", "g"), ("b",)], [("g", "b")]))

    assert [n.id for n in flat.nodes] == ["g", "a", "b"]


# --- diagnostics ----------------------------------------------------------------------


def test_diagnostics_for_a_clean_dag() -> None:
    report = validate_graph(build_graph(spec_example()))

    assert report.is_dag
    assert (report.cycles, report.self_loops, report.isolated_nodes) == ([], [], [])
    assert report.component_count == 1
    assert (report.sources, report.sinks) == (["n1"], ["n5"])


def test_diagnostics_report_cycles_loops_and_isolates() -> None:
    graph = build_graph(
        diagram(
            [("a",), ("b",), ("c",), ("lonely",), ("g", "group")],
            [("a", "b"), ("b", "c"), ("c", "a"), ("b", "b")],
        )
    )

    report = validate_graph(graph)

    assert not report.is_dag
    assert report.cycles == [["a", "b", "c"], ["b"]]
    assert report.self_loops == ["b"]
    assert report.isolated_nodes == ["lonely"]  # the empty group container is not flagged
    assert report.component_count == 2
