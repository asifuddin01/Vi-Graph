"""Evaluation samples: a dataset split, verified against its hashes before use (§18.1).

Reads the dataset layout written by ``data.generator`` (``metadata.jsonl``, ``images/``,
``graphs/``, ``manifest.json``). Only the fields evaluation needs are required, so a
real-diagram set (§15) can use the same layout with fewer metadata fields.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from data.generator.dataset import graph_hash, split_hash

# Metadata fields reported as breakdowns (levels, diagram types, layouts, themes).
BREAKDOWNS = ("level", "diagram_type", "layout", "theme")


class EvalSample(BaseModel):
    id: str
    image: Path
    graph: Path
    image_sha256: str
    graph_sha256: str
    attributes: dict[str, str | int]  # breakdown keys → values


class SplitInfo(BaseModel):
    dataset: str
    directory: str
    split: str
    samples: int  # in the split (a run may use a prefix)
    split_hash: str  # the §18.1 split version
    graph_hash: str
    dataset_hash: str | None = None
    generator_version: str | None = None
    graphviz_version: str | None = None


class SplitError(ValueError):
    pass


def load_split(
    dataset_dir: Path, split: str, *, verify: bool = True
) -> tuple[SplitInfo, list[EvalSample]]:
    """The split's samples in dataset order. With ``verify``, every image and ground-truth
    file is re-hashed and the split hash compared with the manifest's."""
    dataset_dir = dataset_dir.resolve()
    samples = []
    for line in (dataset_dir / "metadata.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["split"] != split:
            continue
        render = row.get("render") or {}
        values = {**row, "layout": render.get("layout"), "theme": render.get("theme")}
        samples.append(
            EvalSample(
                id=row["id"],
                image=dataset_dir / row["image"],
                graph=dataset_dir / row["graph"],
                image_sha256=row["image_sha256"],
                graph_sha256=row["graph_sha256"],
                attributes={k: values[k] for k in BREAKDOWNS if values.get(k) is not None},
            )
        )
    if not samples:
        raise SplitError(f"no samples in split {split!r} of {dataset_dir}")

    problems = []
    if verify:
        for sample in samples:
            if _sha256(sample.image) != sample.image_sha256:
                problems.append(f"{sample.id}: image hash mismatch")
            if _sha256(sample.graph) != sample.graph_sha256:
                problems.append(f"{sample.id}: ground-truth hash mismatch")

    manifest_path = dataset_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    info = SplitInfo(
        dataset=manifest.get("name", dataset_dir.name),
        directory=str(dataset_dir),
        split=split,
        samples=len(samples),
        split_hash=split_hash(samples),
        graph_hash=graph_hash(samples),
        dataset_hash=manifest.get("dataset_hash"),
        generator_version=manifest.get("generator_version"),
        graphviz_version=manifest.get("graphviz_version"),
    )
    expected = manifest.get("split_hashes", {}).get(split)
    if expected is not None and expected != info.split_hash:
        problems.append(f"split {split!r}: hash differs from manifest.json")
    if problems:
        raise SplitError("; ".join(problems[:10]) + (" …" if len(problems) > 10 else ""))
    return info, samples


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
