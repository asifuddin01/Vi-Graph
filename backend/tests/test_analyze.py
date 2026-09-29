import io
import json

import pytest
from PIL import Image

from app import __version__
from app.pipeline.analyze import analyze_image
from app.pipeline.normalize import NormalizationCode
from app.schemas import SCHEMA_VERSION
from app.utils.images import ImageError
from app.vlm import DecodingParams, MockVLM
from app.vlm.mock import DEFAULT_RESPONSE
from app.vlm.prompts import GRAPH_CORRECTION, GRAPH_EXTRACTION

LIMITS = {"max_side": 1024, "max_pixels": 10_000_000}


def png(width: int = 1600, height: int = 800) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_successful_analysis_records_everything_needed_to_reproduce_it() -> None:
    params = DecodingParams(temperature=0.2, top_p=0.9, seed=42)

    record = analyze_image(MockVLM(), png(), params=params, split_version="split-abc", **LIMITS)

    meta = record.metadata
    assert meta.app_version == __version__
    assert meta.schema_version == SCHEMA_VERSION
    assert (meta.model.backend, meta.model.model_id) == ("mock", "vigraph/mock-vlm")
    assert meta.params == params
    assert (meta.prompt_id, meta.prompt_sha256) == (GRAPH_EXTRACTION.id, GRAPH_EXTRACTION.sha256)
    assert meta.correction_prompt_sha256 == GRAPH_CORRECTION.sha256
    assert meta.split_version == "split-abc"
    assert meta.image_max_side == 1024
    assert record.image.original_size == (1600, 800)
    assert record.image.size == (1024, 512)
    assert record.image.format == "PNG"
    assert len(record.id) == 32
    assert record.latency_ms >= 0


def test_graph_is_the_normalized_extraction() -> None:
    record = analyze_image(MockVLM(), png(), **LIMITS)

    assert record.extraction.status == "valid_first_attempt"
    assert record.normalization is not None
    assert record.graph == record.normalization.graph
    assert [n.id for n in record.graph.nodes] == ["n1", "n2", "n3", "n4", "n5"]


def test_normalization_runs_on_repaired_output() -> None:
    data = json.loads(DEFAULT_RESPONSE)
    for node in data["nodes"]:
        node["id"] = node["id"].upper()  # N1..N5: valid, but not normal
    for edge in data["edges"]:
        edge["source"], edge["target"] = edge["source"].upper(), edge["target"].upper()
    data["edges"].append({"source": "N1", "target": "ghost", "relation": "flows_to"})
    bad = json.dumps(data)

    record = analyze_image(MockVLM([bad, bad]), png(), **LIMITS)

    assert record.extraction.status == "repaired"
    assert [n.id for n in record.graph.nodes] == ["n1", "n2", "n3", "n4", "n5"]
    assert [c.code for c in record.normalization.changes] == [NormalizationCode.RENUMBERED_IDS]


def test_failed_extraction_has_no_graph() -> None:
    record = analyze_image(MockVLM(["no json here"]), png(), **LIMITS)

    assert record.extraction.status == "failed"
    assert record.normalization is None
    assert record.graph is None


def test_bad_image_is_rejected_before_the_model_runs() -> None:
    vlm = MockVLM()

    with pytest.raises(ImageError):
        analyze_image(vlm, b"not an image", **LIMITS)

    assert vlm.call_count == 0
