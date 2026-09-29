import io
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_analyze_limiter, get_image_store, get_run_store
from app.api.limits import SlidingWindowLimiter
from app.config import Settings, get_settings
from app.main import create_app
from app.storage.images import ImageStore
from app.storage.runs import RunStore
from app.vlm import DecodingParams, Message, MockVLM
from app.vlm.base import Completion, ModelInfo, VLMBackend
from app.vlm.factory import get_vlm_backend
from app.vlm.mock import DEFAULT_RESPONSE


@dataclass
class Env:
    app: FastAPI
    client: TestClient
    vlm: VLMBackend
    runs: RunStore
    images: ImageStore


def make_env(
    tmp_path: Path, vlm: VLMBackend | None = None, *, rate_limit: int = 0, max_upload_mb: int = 1
) -> Env:
    settings = Settings(
        _env_file=None,
        storage_dir=tmp_path,
        max_upload_mb=max_upload_mb,
        analyze_rate_limit_per_minute=rate_limit,
        image_max_side=512,
    )
    vlm = vlm or MockVLM()
    runs = RunStore(tmp_path / "runs.sqlite3")
    images = ImageStore(tmp_path / "images")
    limiter = SlidingWindowLimiter(rate_limit)
    app = create_app(settings)
    app.dependency_overrides.update(
        {
            get_settings: lambda: settings,
            get_vlm_backend: lambda: vlm,
            get_run_store: lambda: runs,
            get_image_store: lambda: images,
            get_analyze_limiter: lambda: limiter,
        }
    )
    return Env(app=app, client=TestClient(app), vlm=vlm, runs=runs, images=images)


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return make_env(tmp_path)


def png(color: str = "white", size: tuple[int, int] = (800, 400)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def upload(env: Env, data: bytes, filename: str = "diagram.png", **form: str):
    return env.client.post("/api/analyze", files={"file": (filename, data, "image/png")}, data=form)


# --- success paths --------------------------------------------------------------------


def test_analyze_returns_the_graph_and_raw_output(env: Env) -> None:
    response = upload(env, png())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "valid_first_attempt"
    assert body["schema_version"] == "2.0"
    assert [n["label"] for n in body["graph"]["nodes"]][:2] == ["Input Image", "CNN Encoder"]
    assert body["mermaid"].startswith("flowchart TD\n")
    assert 'n4{{"Feature Fusion"}}' in body["mermaid"]
    assert body["attempts"][0]["raw_output"] == DEFAULT_RESPONSE
    assert body["metrics"] == {
        "latency_ms": body["metrics"]["latency_ms"],
        "attempts": 1,
        "repairs": 0,
        "normalization_changes": 0,
        "nodes": 5,
        "edges": 5,
        "cached": False,
    }
    assert body["model"]["backend"] == "mock"
    assert body["image"]["original_size"] == [800, 400]
    assert body["image"]["size"] == [512, 256]
    assert body["failure_reason"] is None


def test_run_and_image_are_stored(env: Env) -> None:
    body = upload(env, png(), filename="../../etc/passwd.png").json()

    assert env.runs.get(body["diagram_id"]) is not None
    stored = list(env.images.root.iterdir())
    assert [p.name for p in stored] == [f"{body['image']['sha256']}.png"]


def test_identical_upload_is_served_from_cache(env: Env) -> None:
    first = upload(env, png()).json()

    second = upload(env, png()).json()

    assert second["metrics"]["cached"] is True
    assert second["diagram_id"] == first["diagram_id"]
    assert env.vlm.call_count == 1


def test_different_image_is_not_cached(env: Env) -> None:
    upload(env, png("white"))

    body = upload(env, png("black")).json()

    assert body["metrics"]["cached"] is False
    assert env.vlm.call_count == 2


def test_repaired_output_reports_its_repairs(tmp_path: Path) -> None:
    data = json.loads(DEFAULT_RESPONSE)
    data["edges"].append({"source": "n1", "target": "n42", "relation": "flows_to"})
    env = make_env(tmp_path, MockVLM([json.dumps(data)]))

    body = upload(env, png()).json()

    assert body["status"] == "repaired"
    assert [r["code"] for r in body["repairs"]] == ["dropped_edge"]
    assert [a["valid"] for a in body["attempts"]] == [False, False]
    assert body["metrics"]["edges"] == 5


def test_failed_extraction_is_a_structured_failure_and_is_not_cached(tmp_path: Path) -> None:
    env = make_env(tmp_path, MockVLM(["I see some boxes."]))

    body = upload(env, png()).json()
    upload(env, png())

    assert body["status"] == "failed"
    assert body["graph"] is None
    assert body["failure_reason"] == "no attempt contained a JSON object"
    assert body["mermaid"] is None
    assert body["metrics"]["nodes"] is None
    assert env.runs.get(body["diagram_id"]) is not None  # failures are logged too
    assert env.vlm.call_count == 4  # the second upload ran again: failures are not cached


def test_matching_model_field_is_accepted(env: Env) -> None:
    assert upload(env, png(), model="vigraph/mock-vlm").status_code == 200


def test_get_analysis_returns_the_stored_result(env: Env) -> None:
    created = upload(env, png()).json()

    fetched = env.client.get(f"/api/analyses/{created['diagram_id']}")

    assert fetched.status_code == 200
    assert fetched.json()["graph"] == created["graph"]


@pytest.mark.parametrize("diagram_id", ["0" * 32, "not-an-id", "../../etc/passwd"])
def test_unknown_analysis_is_404(env: Env, diagram_id: str) -> None:
    assert env.client.get(f"/api/analyses/{diagram_id}").status_code == 404


# --- rejections -----------------------------------------------------------------------


def test_invalid_image_is_rejected_without_running_the_model(env: Env) -> None:
    response = upload(env, b"%PDF-1.7 not an image", filename="paper.png")

    assert response.status_code == 422
    assert response.json()["detail"] == "the file is not a readable image"
    assert env.vlm.call_count == 0
    assert env.runs.recent() == []


def test_missing_file_is_rejected(env: Env) -> None:
    assert env.client.post("/api/analyze", data={"model": "x"}).status_code == 422


def test_unavailable_model_is_rejected(env: Env) -> None:
    response = upload(env, png(), model="some/other-model")

    assert response.status_code == 422
    assert "not available" in response.json()["detail"]


def test_oversized_upload_is_rejected_by_content_length(env: Env) -> None:
    response = upload(env, b"\0" * (2 * 1024 * 1024))

    assert response.status_code == 413
    assert env.vlm.call_count == 0


def test_oversized_chunked_upload_is_cut_off_while_streaming(env: Env) -> None:
    boundary = "vigraph-test-boundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="big.png"\r\nContent-Type: image/png\r\n\r\n'
    ).encode()

    def body():  # a generator makes the client send it chunked, without Content-Length
        yield head
        for _ in range(40):
            yield b"\0" * 64 * 1024
        yield f"\r\n--{boundary}--\r\n".encode()

    response = env.client.post(
        "/api/analyze",
        content=body(),
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )

    assert response.status_code == 413
    # The middleware's message, not the endpoint's post-parse "file is larger than" check.
    assert response.json()["detail"] == "request body is larger than 1 MB"
    assert env.vlm.call_count == 0


def test_rate_limit_returns_429_with_retry_after(tmp_path: Path) -> None:
    env = make_env(tmp_path, rate_limit=2)

    statuses = [upload(env, png(color)).status_code for color in ("white", "black", "red")]

    assert statuses == [200, 200, 429]
    response = upload(env, png("blue"))
    assert int(response.headers["retry-after"]) >= 1


class ExplodingVLM(VLMBackend):
    @property
    def info(self) -> ModelInfo:
        return ModelInfo(backend="test", model_id="exploding")

    def _generate(self, messages: Sequence[Message], params: DecodingParams) -> Completion:
        raise RuntimeError("CUDA out of memory (secret internal detail)")


def test_model_failure_is_503_without_leaking_details(tmp_path: Path) -> None:
    env = make_env(tmp_path, ExplodingVLM())

    response = upload(env, png())

    assert response.status_code == 503
    assert "secret" not in response.text
