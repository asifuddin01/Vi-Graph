import json
import zipfile
from pathlib import Path

import pytest

from evaluation.samples import SplitInfo
from training.qlora.config import load_config
from training.qlora.handback import package_handback
from training.qlora.train import (
    RUN_CONFIG,
    ResumeMismatch,
    environment,
    fingerprint,
    projected_hours,
    resume_guard,
    total_steps,
)

CONFIG = Path(__file__).resolve().parents[2] / "training" / "configs" / "qlora_t4.yaml"


def split(name: str, split_hash: str = "a" * 64) -> SplitInfo:
    return SplitInfo(
        dataset="synthetic-v1",
        directory="/content/data",
        split=name,
        samples=10,
        split_hash=split_hash,
        graph_hash="b" * 64,
    )


def test_resume_guard_records_then_requires_the_same_run(tmp_path: Path) -> None:
    config = load_config(CONFIG)
    current = fingerprint(config, split("train"), split("val"))

    assert resume_guard(tmp_path / "run", current) is False
    assert (tmp_path / "run" / RUN_CONFIG).exists()
    assert resume_guard(tmp_path / "run", current) is True


def test_resume_guard_refuses_a_different_config_or_data_build(tmp_path: Path) -> None:
    config = load_config(CONFIG)
    resume_guard(tmp_path, fingerprint(config, split("train"), split("val")))

    other_config = load_config(CONFIG, **{"lora.r": 8})
    with pytest.raises(ResumeMismatch, match="config"):
        resume_guard(tmp_path, fingerprint(other_config, split("train"), split("val")))
    with pytest.raises(ResumeMismatch, match="train_split"):
        resume_guard(tmp_path, fingerprint(config, split("train", "c" * 64), split("val")))


def test_the_directory_of_a_split_does_not_matter_on_resume(tmp_path: Path) -> None:
    config = load_config(CONFIG)
    resume_guard(tmp_path, fingerprint(config, split("train"), split("val")))
    moved = split("train").model_copy(update={"directory": "/content/elsewhere"})

    assert resume_guard(tmp_path, fingerprint(config, moved, split("val"))) is True


def test_step_and_time_projections() -> None:
    assert total_steps(2000, 2, 16, None) == 250
    assert total_steps(2000, 1.5, 16, None) == 188
    assert total_steps(2000, 2, 16, 7) == 7
    assert projected_hours(4.5, 2000, 2) == pytest.approx(5.0)


def test_environment_reports_python_and_git() -> None:
    info = environment()

    assert info["python"] and "packages" in info
    assert info["git_commit"] is None or len(info["git_commit"]) == 40


def test_handback_zip_has_files_manifest_and_missing_list(tmp_path: Path) -> None:
    run = tmp_path / "qwen3vl-2b-qlora-v1"
    (run / "adapter").mkdir(parents=True)
    (run / "training_run.json").write_text("{}")
    (run / "train_log.jsonl").write_text('{"loss": 1.0}\n')
    (run / "adapter" / "adapter_config.json").write_text('{"r": 16}')
    (run / "adapter" / "adapter_model.safetensors").write_bytes(b"\x00" * 64)
    evaluation = tmp_path / "zeroshot-s0"
    evaluation.mkdir()
    for name in ("run.json", "summary.json", "report.md", "predictions.jsonl.gz"):
        (evaluation / name).write_text(name)
    comparison = tmp_path / "qlora-vs-zeroshot.md"
    comparison.write_text("# Paired comparison")

    manifest = package_handback(
        tmp_path / "out" / "handback.zip",
        training_dirs=[run],
        eval_dirs=[evaluation],
        extra_files=[comparison],
        environment={"gpu": "Tesla T4"},
    )

    assert manifest["missing"] == ["training/qwen3vl-2b-qlora-v1/run_config.json"]
    with zipfile.ZipFile(tmp_path / "out" / "handback.zip") as archive:
        names = set(archive.namelist())
        stored = json.loads(archive.read("MANIFEST.json"))
    assert "training/qwen3vl-2b-qlora-v1/adapter/adapter_model.safetensors" in names
    assert "evaluation/zeroshot-s0/predictions.jsonl.gz" in names
    assert "extra/qlora-vs-zeroshot.md" in names
    assert stored == manifest and stored["environment"] == {"gpu": "Tesla T4"}
    sizes = {f["path"]: f["bytes"] for f in stored["files"]}
    assert sizes["training/qwen3vl-2b-qlora-v1/adapter/adapter_model.safetensors"] == 64
