import json
from pathlib import Path

import pytest

from app.vlm.factory import get_vlm_backend
from tests.api_env import Env, make_env, png, upload
from tests.vlm_doubles import RecordingVLM


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return make_env(tmp_path)


def ask(env: Env, diagram_id: str, question: str):
    return env.client.post("/api/qa", json={"diagram_id": diagram_id, "question": question})


def analyzed(env: Env) -> str:
    return upload(env, png()).json()["diagram_id"]


def test_graph_question(env: Env) -> None:
    diagram_id = analyzed(env)

    response = ask(env, diagram_id, "Which branches operate in parallel?")

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == (
        "After Input Image, CNN Encoder and Transformer Encoder run in parallel and merge at "
        "Feature Fusion."
    )
    assert body["source"] == "graph"
    assert body["route"] == {"category": "structural", "intent": "parallel", "needs_image": False}
    assert sorted(body["grounding"]["nodes"]) == ["n1", "n2", "n3", "n4"]
    assert ["n1", "n2"] in body["grounding"]["edges"]
    assert (body["graph_version"], body["model"]) == (None, None)


def test_answers_use_the_latest_saved_edit(env: Env) -> None:
    result = upload(env, png()).json()
    graph = json.loads(json.dumps(result["graph"]))
    graph["nodes"][4]["label"] = "Softmax Head"
    env.client.put(f"/api/analyses/{result['diagram_id']}/graph", json={"graph": graph})

    body = ask(env, result["diagram_id"], "What is the final output?").json()

    assert body["answer"] == "The final output is Softmax Head."
    assert body["graph_version"] == 1


def test_visual_question_with_the_mock_backend_says_it_cannot_see(env: Env) -> None:
    body = ask(env, analyzed(env), "What color is the CNN Encoder?").json()

    assert body["source"] == "none"
    assert body["answer"] == (
        "Answering this needs the image, but the server is running the mock VLM, which "
        "can't look at images."
    )
    assert body["route"]["needs_image"] is True


def test_visual_question_goes_to_a_real_model_with_the_stored_image(tmp_path: Path) -> None:
    vlm = RecordingVLM()
    env = make_env(tmp_path)
    diagram_id = analyzed(env)  # analyzed with the mock ...
    env.app.dependency_overrides[get_vlm_backend] = lambda: vlm  # ... then asked with a model

    body = ask(env, diagram_id, "What color is the CNN Encoder?").json()

    assert (body["source"], body["answer"]) == ("vlm", "The encoder boxes are drawn in blue.")
    assert body["model"]["model_id"] == "recording-vlm"
    [message] = vlm.calls[0]
    assert message.images[0].size == (512, 256)  # the stored upload, preprocessed again


def test_questions_are_logged_and_listed_newest_first(env: Env) -> None:
    diagram_id = analyzed(env)
    ask(env, diagram_id, "What is the final output?")
    ask(env, diagram_id, "How many nodes are present?")

    history = env.client.get(f"/api/analyses/{diagram_id}/qa").json()

    assert [h["question"] for h in history] == [
        "How many nodes are present?",
        "What is the final output?",
    ]
    [latest, _] = env.runs.qa_history(diagram_id)
    assert latest.result.route.intent == "count_nodes"
    assert latest.result.route.rule  # the matched rule is kept for debugging (§28)


def test_question_whitespace_is_normalized(env: Env) -> None:
    body = ask(env, analyzed(env), "  What is   the final\noutput?  ").json()

    assert body["question"] == "What is the final output?"


@pytest.mark.parametrize("question", ["", "x" * 501])
def test_question_length_is_validated(env: Env, question: str) -> None:
    assert ask(env, analyzed(env), question).status_code == 422


def test_unknown_analysis_is_404(env: Env) -> None:
    assert ask(env, "0" * 32, "What is the output?").status_code == 404


def test_qa_rate_limit(tmp_path: Path) -> None:
    env = make_env(tmp_path, qa_rate_limit=2)
    diagram_id = analyzed(env)

    statuses = [ask(env, diagram_id, "What is the output?").status_code for _ in range(3)]

    assert statuses == [200, 200, 429]
