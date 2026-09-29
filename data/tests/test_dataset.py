import json
from collections import Counter
from pathlib import Path

import pytest

from app.exporters.graphviz import graphviz_available
from app.schemas import DiagramGraph
from data.generator.__main__ import main as cli
from data.generator.dataset import (
    TEST_LAYOUTS,
    TEST_THEMES,
    TRAIN_LAYOUTS,
    TRAIN_THEMES,
    Manifest,
    SplitConfig,
    build_dataset,
    default_config,
    load_records,
)

pytestmark = pytest.mark.skipif(not graphviz_available(), reason="Graphviz not installed")


@pytest.fixture(scope="module")
def dataset(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Manifest]:
    out = tmp_path_factory.mktemp("synthetic")
    config = default_config("tiny", seed=7, train=28, val=8, test=16, iid_test=4)
    return out, build_dataset(config, out, workers=4)


def test_files_and_manifest(dataset: tuple[Path, Manifest]) -> None:
    out, manifest = dataset

    records = load_records(out)
    assert manifest.counts == {"train": 28, "val": 8, "test": 16, "test_iid": 4}
    assert len(records) == 56
    assert len(list((out / "images").glob("*.png"))) == 56
    assert (out / "splits" / "test.txt").read_text().split() == [f"test-{i:06d}" for i in range(16)]
    for record in records[:10]:
        graph = DiagramGraph.model_validate_json((out / record.graph).read_text())
        assert graph.diagram_type.value == record.diagram_type
        assert (out / record.image).read_bytes().startswith(b"\x89PNG")
    assert manifest.schema_version == "2.0"
    assert "graphviz version" in manifest.graphviz_version
    assert set(manifest.split_hashes) == {"train", "val", "test", "test_iid"}


def test_splits_are_stratified_over_levels_and_types(dataset: tuple[Path, Manifest]) -> None:
    out, _ = dataset

    train = load_records(out, "train")

    assert Counter(r.level for r in train) == {1: 7, 2: 7, 3: 7, 4: 7}
    assert len({r.diagram_type for r in train}) == 7


def test_test_split_uses_held_out_layouts_and_themes(dataset: tuple[Path, Manifest]) -> None:
    out, manifest = dataset

    for record in load_records(out, "test"):
        assert record.render.layout in TEST_LAYOUTS
        assert record.render.theme in TEST_THEMES
    for record in load_records(out, "train") + load_records(out, "val"):
        assert record.render.layout in TRAIN_LAYOUTS
        assert record.render.theme in TRAIN_THEMES
    assert not set(TEST_LAYOUTS) & set(TRAIN_LAYOUTS)
    assert not set(TEST_THEMES) & set(TRAIN_THEMES)
    held_out = {s.name for s in manifest.config.splits if s.held_out}
    assert held_out == {"test", "test_iid"}


def test_building_twice_gives_identical_hashes(
    dataset: tuple[Path, Manifest], tmp_path: Path
) -> None:
    _, first = dataset

    second = build_dataset(first.config, tmp_path / "again", workers=2)

    assert second.split_hashes == first.split_hashes
    assert second.graph_hashes == first.graph_hashes
    assert second.dataset_hash == first.dataset_hash


def test_verify_passes_and_detects_tampering(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    out = tmp_path / "ds"
    build_dataset(default_config("small", train=4, val=0, test=4), out)

    assert cli(["verify", str(out)]) == 0
    image = out / "images" / "train-000001.png"
    image.write_bytes(image.read_bytes() + b"x")
    assert cli(["verify", str(out)]) == 1
    assert "train-000001: image hash mismatch" in capsys.readouterr().err


def test_verify_against_a_reference_manifest(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    out = tmp_path / "ds"
    manifest = build_dataset(default_config("small", train=4, val=0, test=4), out)
    same = tmp_path / "same.json"
    same.write_text(manifest.model_dump_json())
    other = tmp_path / "other.json"
    other.write_text(manifest.model_copy(update={"graph_hashes": {"train": "x"}}).model_dump_json())

    assert cli(["verify", str(out), "--reference", str(same)]) == 0
    assert cli(["verify", str(out), "--reference", str(other)]) == 1
    assert "ground truth differs" in capsys.readouterr().err


def test_verify_detects_edited_ground_truth(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    out = tmp_path / "ds"
    build_dataset(default_config("small", train=4, val=0, test=0), out)
    gt = out / "graphs" / "train-000002.json"
    gt.write_text(gt.read_text().replace('"label": "', '"label": "X', 1))

    assert cli(["verify", str(out)]) == 1
    assert "train-000002: graph hash mismatch" in capsys.readouterr().err


def test_refuses_to_overwrite_a_non_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "existing.txt").write_text("keep me")

    with pytest.raises(FileExistsError):
        build_dataset(default_config(train=1, val=0, test=0), tmp_path)


def test_split_config_validation() -> None:
    with pytest.raises(ValueError, match="unknown layouts"):
        SplitConfig(name="x", size=1, layouts=["spiral"], themes=["classic"])
    with pytest.raises(ValueError, match="can draw groups"):
        SplitConfig(name="x", size=1, layouts=["radial"], themes=["classic"])


def test_cli_build(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    out = tmp_path / "cli"

    assert cli(["build", "--out", str(out), "--train", "4", "--val", "0", "--test", "4"]) == 0

    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["counts"] == {"train": 4, "test": 4}
    assert "dataset hash" in capsys.readouterr().out


def test_cli_stats(dataset: tuple[Path, Manifest], capsys: pytest.CaptureFixture) -> None:
    out, _ = dataset

    assert cli(["stats", str(out)]) == 0

    stats = json.loads(capsys.readouterr().out)
    assert set(stats) == {"train", "val", "test", "test_iid"}
    assert stats["train"]["samples"] == 28
    assert set(stats["train"]["levels"]) == {"L1", "L2", "L3", "L4"}
    assert set(stats["test"]["layouts"]) <= set(TEST_LAYOUTS)
    assert sum(stats["test"]["themes"].values()) == 16
