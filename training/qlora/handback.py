"""Package what a Colab run produced into one zip to give back (spec §33.4).

The zip holds the trained adapter, the training metadata and log, every evaluation run
(run.json, summary.json, report.md, predictions.jsonl.gz), comparisons, and the
environment — each listed in MANIFEST.json with its size and sha256. Raw checkpoints and
the dataset are left out: they are large and reproducible.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

TRAINING_FILES = (
    "training_run.json",
    "run_config.json",
    "train_log.jsonl",
    "adapter/adapter_config.json",
    "adapter/adapter_model.safetensors",
)
EVALUATION_FILES = ("run.json", "summary.json", "report.md", "predictions.jsonl.gz")


def package_handback(
    out_zip: Path,
    *,
    training_dirs: list[Path] = (),
    eval_dirs: list[Path] = (),
    extra_files: list[Path] = (),
    environment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``out_zip``; returns the manifest (also stored in the zip as MANIFEST.json).
    Missing expected files are listed under ``missing`` rather than failing the package."""
    entries: list[tuple[str, Path]] = []
    missing: list[str] = []
    for directory in training_dirs:
        for name in TRAINING_FILES:
            _add(entries, missing, f"training/{directory.name}/{name}", directory / name)
    for directory in eval_dirs:
        for name in EVALUATION_FILES:
            _add(entries, missing, f"evaluation/{directory.name}/{name}", directory / name)
    for path in extra_files:
        _add(entries, missing, f"extra/{path.name}", path)

    manifest = {
        "files": [
            {"path": arcname, "bytes": path.stat().st_size, "sha256": _sha256(path)}
            for arcname, path in entries
        ],
        "missing": missing,
        "environment": environment or {},
    }
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for arcname, path in entries:
            archive.write(path, arcname)
        archive.writestr("MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    return manifest


def _add(entries: list[tuple[str, Path]], missing: list[str], arcname: str, path: Path) -> None:
    if path.is_file():
        entries.append((arcname, path))
    else:
        missing.append(arcname)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
