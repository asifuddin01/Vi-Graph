from app.pipeline.validation import format_problem_list, validate_graph


def graph(**overrides: object) -> dict:
    return {
        "schema_version": "2.0",
        "diagram_type": "flowchart",
        "nodes": [
            {"id": "n1", "label": "Start", "type": "input"},
            {"id": "n2", "label": "End", "type": "output"},
        ],
        "edges": [{"source": "n1", "target": "n2", "relation": "flows_to"}],
        **overrides,
    }


def test_valid_graph_has_no_problems() -> None:
    parsed, problems = validate_graph(graph())

    assert parsed is not None
    assert problems == []


def test_structural_problems_are_listed_individually() -> None:
    data = graph(edges=[{"source": "n1", "target": "n9", "relation": "flows_to"}])
    data["nodes"].append({"id": "n1", "label": "Again", "type": "module"})

    parsed, problems = validate_graph(data)

    assert parsed is None
    assert problems == [
        "duplicate node id 'n1' is used by 2 nodes",
        "edge #0 'n1->n9' references node id 'n9', which does not exist",
    ]


def test_field_problems_name_the_path_and_the_bad_value() -> None:
    data = graph()
    data["nodes"][1]["type"] = "layer"

    _, problems = validate_graph(data)

    assert len(problems) == 1
    assert problems[0].startswith("nodes[1].type: Input should be 'input', 'module'")
    assert problems[0].endswith("(got 'layer')")


def test_value_error_prefix_is_removed() -> None:
    _, problems = validate_graph(graph(schema_version="1.0"))

    assert problems == [
        "schema_version: unsupported schema_version '1.0' (supported: 2.0) (got '1.0')"
    ]


def test_missing_and_extra_fields_do_not_echo_input() -> None:
    data = graph(notes="hi")
    del data["nodes"][0]["label"]

    _, problems = validate_graph(data)

    assert "nodes[0].label: Field required" in problems
    assert "notes: Extra inputs are not permitted" in problems


def test_problem_list_is_capped() -> None:
    text = format_problem_list([f"problem {i}" for i in range(25)], limit=20)

    lines = text.splitlines()
    assert len(lines) == 21
    assert lines[0] == "- problem 0"
    assert lines[-1] == "- ... and 5 more"
