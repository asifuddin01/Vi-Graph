import io
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from app.pipeline.analyze import AnalysisRecord, analyze_image
from app.storage.runs import RunStore
from app.vlm import DecodingParams, MockVLM, ModelInfo

LIMITS = {"max_side": 512, "max_pixels": 10_000_000}


def png(color: str = "white") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buffer, format="PNG")
    return buffer.getvalue()


def run(data: bytes | None = None, **kwargs: object) -> AnalysisRecord:
    responses = kwargs.pop("responses", None)
    return analyze_image(MockVLM(responses), data or png(), **LIMITS, **kwargs)  # type: ignore[arg-type]


@pytest.fixture
def store(tmp_path: Path) -> RunStore:
    return RunStore(tmp_path / "nested" / "vigraph.sqlite3")


def test_database_is_created_with_a_schema_version(store: RunStore) -> None:
    assert store.path.exists()
    with sqlite3.connect(store.path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3


def test_reopening_an_existing_database_keeps_its_runs(store: RunStore) -> None:
    record = run()
    store.save(record)

    reopened = RunStore(store.path)

    assert reopened.get(record.id) == record


def test_saved_record_round_trips(store: RunStore) -> None:
    record = run(responses=["not json", "still not json"])

    store.save(record)

    assert store.get(record.id) == record


def test_unknown_run_is_none(store: RunStore) -> None:
    assert store.get("does-not-exist") is None


def test_reproducibility_fields_are_queryable_columns(store: RunStore) -> None:
    record = run(params=DecodingParams(temperature=0.4, seed=9), split_version="split-1")
    store.save(record)

    with sqlite3.connect(store.path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (record.id,)).fetchone()

    assert row["model_id"] == "vigraph/mock-vlm"
    assert row["prompt_sha256"] == record.metadata.prompt_sha256
    assert (row["temperature"], row["seed"]) == (0.4, 9)
    assert row["split_version"] == "split-1"
    assert row["status"] == "valid_first_attempt"
    assert (row["attempts"], row["repair_count"]) == (1, 0)
    assert row["image_sha256"] == record.image.sha256


def test_recent_lists_newest_first(store: RunStore) -> None:
    records = [run(), run(), run()]
    for record in records:
        store.save(record)

    assert [r.id for r in store.recent(limit=2)] == [records[2].id, records[1].id]


def test_cache_hits_on_identical_inputs(store: RunStore) -> None:
    record = run()
    store.save(record)

    assert store.find_cached(record.image.sha256, record.metadata) == record


@pytest.mark.parametrize(
    "change",
    [
        {"params": DecodingParams(seed=1)},
        {"params": DecodingParams(max_new_tokens=100)},
        {"params": DecodingParams(runaway_guard="1")},
        {"model": ModelInfo(backend="hf", model_id="vigraph/mock-vlm", revision="1")},
        {"model": ModelInfo(backend="mock", model_id="vigraph/mock-vlm", revision="2")},
        {
            "model": ModelInfo(
                backend="mock", model_id="vigraph/mock-vlm", revision="1", adapter_path="adapters/a"
            )
        },
        {"prompt_sha256": "0" * 64},
        {"app_version": "9.9.9"},
        {"image_max_side": 1024},
    ],
    ids=[
        "seed",
        "max-tokens",
        "runaway-guard",
        "backend",
        "revision",
        "adapter",
        "prompt",
        "app-version",
        "image-max-side",
    ],
)
def test_cache_misses_when_any_input_differs(store: RunStore, change: dict) -> None:
    record = run()
    store.save(record)
    metadata = record.metadata.model_copy(update=change)

    assert store.find_cached(record.image.sha256, metadata) is None


def test_cache_misses_for_a_different_image(store: RunStore) -> None:
    record = run()
    store.save(record)

    assert store.find_cached(run(png("black")).image.sha256, record.metadata) is None


def test_failed_runs_are_never_served_from_cache(store: RunStore) -> None:
    record = run(responses=["no json"])
    store.save(record)

    assert record.extraction.status == "failed"
    assert store.find_cached(record.image.sha256, record.metadata) is None


# --- graph versions (editor saves) ----------------------------------------------------


def test_version_1_database_gains_the_newer_tables(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    RunStore(path)
    with sqlite3.connect(path) as conn:  # turn it back into a version 1 database
        conn.execute("DROP TABLE graph_versions")
        conn.execute("DROP TABLE qa_log")
        conn.execute("PRAGMA user_version=1")

    RunStore(path)

    with sqlite3.connect(path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
        assert {"graph_versions", "qa_log"} <= tables
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 3


def test_no_edits_means_no_version(store: RunStore) -> None:
    record = run()
    store.save(record)

    assert store.latest_graph_version(record.id) is None


def test_saved_versions_count_up_and_the_latest_wins(store: RunStore) -> None:
    record = run()
    store.save(record)
    graph = record.graph
    renamed = graph.model_copy(
        update={"nodes": [graph.nodes[0].model_copy(update={"label": "Edited"}), *graph.nodes[1:]]}
    )

    first = store.save_graph_version(record.id, graph, {"n1": (0.0, 0.0)})
    second = store.save_graph_version(record.id, renamed)

    assert (first.version, second.version) == (1, 2)
    latest = store.latest_graph_version(record.id)
    assert latest == second
    assert latest.graph.nodes[0].label == "Edited"
    assert latest.layout is None


def test_layout_round_trips(store: RunStore) -> None:
    record = run()
    store.save(record)

    store.save_graph_version(record.id, record.graph, {"n1": (10.5, -3.0), "n2": (200, 40)})

    assert store.latest_graph_version(record.id).layout == {"n1": (10.5, -3.0), "n2": (200.0, 40.0)}


def test_versions_are_kept_per_analysis(store: RunStore) -> None:
    a, b = run(), run(png("black"))
    store.save(a)
    store.save(b)

    store.save_graph_version(a.id, a.graph)
    store.save_graph_version(a.id, a.graph)
    store.save_graph_version(b.id, b.graph)

    assert store.latest_graph_version(a.id).version == 2
    assert store.latest_graph_version(b.id).version == 1


def test_the_models_reconstruction_is_never_overwritten(store: RunStore) -> None:
    record = run()
    store.save(record)
    edited = record.graph.model_copy(update={"nodes": record.graph.nodes[:1], "edges": []})

    store.save_graph_version(record.id, edited)

    assert store.get(record.id) == record
