import pytest

from app.qa.router import route_question

SPEC_EXAMPLES = [
    # §12.2 Direct
    ("What comes after the CNN Encoder?", "direct", "successors"),
    ("What is the final output?", "direct", "sinks"),
    ("How many nodes are present?", "direct", "count_nodes"),
    # §12.2 Structural
    ("Which nodes are connected directly to Fusion?", "structural", "neighbors"),
    ("Which branches operate in parallel?", "structural", "parallel"),
    ("What are all paths from Input to Classifier?", "structural", "paths"),
    ("Which nodes have multiple outgoing edges?", "structural", "fan_out"),
    # §12.2 Comparative
    ("Which branch is deeper?", "comparative", "deeper_branch"),
    ("Which component receives outputs from both branches?", "comparative", "common_successor"),
    # §12.2 Explanation
    ("Explain the data flow from input to output.", "explanation", "explain_flow"),
    ("Explain where the branches merge.", "explanation", "explain_merge"),
    # §12.1 / §35 mixed
    ("Why does the Skip branch connect to Addition?", "mixed", "why"),
]

MORE_EXAMPLES = [
    ("What color is the CNN Encoder box?", "visual", "describe_visual"),
    ("Is this label handwritten?", "visual", "describe_visual"),
    ("What shape is the decision node?", "visual", "describe_visual"),
    ("What feeds into Feature Fusion?", "direct", "predecessors"),
    ("What are the inputs to Feature Fusion?", "direct", "predecessors"),
    ("What does the CNN Encoder feed?", "direct", "successors"),
    ("What is the input?", "direct", "sources"),
    ("How many edges are there?", "direct", "count_edges"),
    ("Is there a feedback loop?", "structural", "cycles"),
    ("What is inside the ResNet Block?", "structural", "group_members"),
    ("Which nodes merge information?", "structural", "fan_in"),
    ("What is the longest path?", "comparative", "longest_path"),
    ("Analyze the topology", "explanation", "topology_summary"),
    ("What does this diagram show?", "explanation", "explain_flow"),
    ("How does Input Image reach Classifier?", "structural", "paths"),
    ("What comes after the Output Layer?", "direct", "successors"),
]


@pytest.mark.parametrize(("question", "category", "intent"), SPEC_EXAMPLES + MORE_EXAMPLES)
def test_routing(question: str, category: str, intent: str) -> None:
    route = route_question(question)

    assert (route.category, route.intent) == (category, intent)


def test_routing_ignores_case_and_spacing() -> None:
    assert route_question("  WHAT   COMES\nAFTER  x ").intent == "successors"


def test_unmatched_question_is_unknown() -> None:
    route = route_question("hello there")

    assert (route.category, route.intent, route.rule) == ("unknown", "unknown", "")


@pytest.mark.parametrize(
    ("question", "needs_image"),
    [("What color is it?", True), ("Why is it there?", True), ("What comes after X?", False)],
)
def test_needs_image(question: str, needs_image: bool) -> None:
    assert route_question(question).needs_image is needs_image


def test_matched_rule_is_recorded_for_debugging() -> None:
    assert "parallel" in route_question("Which branches operate in parallel?").rule
