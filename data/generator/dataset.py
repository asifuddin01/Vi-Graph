"""Build a synthetic dataset: images, ground truth, metadata, splits, manifest (spec §13–16).

Layout of an output directory::

    images/<id>.png        rendered diagram
    graphs/<id>.json       ground truth, schema v2
    metadata.jsonl         one record per sample (graph spec, render parameters, hashes)
    splits/<split>.txt     sample ids per split
    manifest.json          config, versions, counts, split hashes

Splits are stratified over difficulty levels and diagram types. The default test split
uses layouts and visual themes never seen in training (§16: "train on horizontal, test on
vertical + radial"), so scores measure diagram reading, not template memorization. Each
split is pinned by a hash over its samples' ids, image hashes, and ground-truth hashes
(§18.1). Rendered pixels depend on the Graphviz version, so each split also gets a
renderer-independent hash over ids and ground truth only: a rebuild elsewhere (e.g. Colab)
must match it exactly, even when the image hashes differ. Samples are seeded individually,
so any one can be regenerated alone.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, Self

from pydantic import BaseModel, model_validator

from app.schemas import SCHEMA_VERSION
from data.generator.graphs import (
    DIAGRAM_TYPES,
    GENERATOR_VERSION,
    LEVELS,
    GeneratedGraph,
    GraphSpec,
    generate_graph,
)
from data.generator.render import (
    CLUSTER_LAYOUTS,
    LAYOUTS,
    THEMES,
    RenderParams,
    graphviz_version,
    render,
    sample_params,
)

MAX_RENDER_ATTEMPTS = 3


class SplitConfig(BaseModel):
    name: str
    size: int
    layouts: list[str]
    themes: list[str]
    held_out: bool = False  # never to be used for training or model selection

    @model_validator(mode="after")
    def _check(self) -> Self:
        if unknown := set(self.layouts) - set(LAYOUTS):
            raise ValueError(f"unknown layouts {sorted(unknown)}")
        if unknown := set(self.themes) - set(THEMES):
            raise ValueError(f"unknown themes {sorted(unknown)}")
        if not set(self.layouts) & CLUSTER_LAYOUTS:
            raise ValueError(f"split {self.name!r} needs a layout that can draw groups")
        return self


class DatasetConfig(BaseModel):
    name: str
    seed: int
    levels: list[int]
    diagram_types: list[str]
    splits: list[SplitConfig]


TRAIN_LAYOUTS = ["layered_lr", "force"]
TRAIN_THEMES = ["classic", "pastel", "corporate", "vivid", "sketch"]
TEST_LAYOUTS = ["layered_tb", "radial", "circular"]
TEST_THEMES = ["dark", "blueprint", "paper"]


def default_config(
    name: str = "synthetic-v1",
    *,
    seed: int = 0,
    train: int = 2000,
    val: int = 300,
    test: int = 500,
    iid_test: int = 0,
) -> DatasetConfig:
    """Spec §32 sizes; the test split uses held-out layouts and themes (§16)."""
    splits = [
        SplitConfig(name="train", size=train, layouts=TRAIN_LAYOUTS, themes=TRAIN_THEMES),
        SplitConfig(name="val", size=val, layouts=TRAIN_LAYOUTS, themes=TRAIN_THEMES),
        SplitConfig(
            name="test", size=test, layouts=TEST_LAYOUTS, themes=TEST_THEMES, held_out=True
        ),
    ]
    if iid_test:
        splits.append(
            SplitConfig(
                name="test_iid",
                size=iid_test,
                layouts=TRAIN_LAYOUTS,
                themes=TRAIN_THEMES,
                held_out=True,
            )
        )
    return DatasetConfig(
        name=name,
        seed=seed,
        levels=sorted(LEVELS),
        diagram_types=list(DIAGRAM_TYPES),
        splits=[s for s in splits if s.size > 0],
    )


class SampleRecord(BaseModel):
    id: str
    split: str
    seed: str
    level: int
    diagram_type: str
    image: str  # path relative to the dataset directory
    graph: str
    image_sha256: str
    graph_sha256: str
    width: int
    height: int
    render_attempts: int
    spec: GraphSpec
    render: RenderParams


class Manifest(BaseModel):
    name: str
    created_at: datetime
    generator_version: str
    schema_version: str
    graphviz_version: str
    config: DatasetConfig
    counts: dict[str, int]
    split_hashes: dict[str, str]
    graph_hashes: dict[str, str]  # ground truth only; independent of the Graphviz version
    dataset_hash: str


def build_dataset(
    config: DatasetConfig, out_dir: Path, *, workers: int = 4, overwrite: bool = False
) -> Manifest:
    if out_dir.exists() and any(out_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"{out_dir} is not empty (pass overwrite=True to replace)")
    for sub in ("images", "graphs", "splits"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    jobs = [(split, index) for split in config.splits for index in range(split.size)]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        records = list(pool.map(lambda job: _make_sample(config, *job, out_dir), jobs))

    with (out_dir / "metadata.jsonl").open("w") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")
    split_hashes, graph_hashes = {}, {}
    for split in config.splits:
        members = [r for r in records if r.split == split.name]
        (out_dir / "splits" / f"{split.name}.txt").write_text("".join(f"{r.id}\n" for r in members))
        split_hashes[split.name] = split_hash(members)
        graph_hashes[split.name] = graph_hash(members)

    manifest = Manifest(
        name=config.name,
        created_at=datetime.now(UTC),
        generator_version=GENERATOR_VERSION,
        schema_version=SCHEMA_VERSION,
        graphviz_version=graphviz_version(),
        config=config,
        counts={split.name: split.size for split in config.splits},
        split_hashes=split_hashes,
        graph_hashes=graph_hashes,
        dataset_hash=hashlib.sha256(json.dumps(split_hashes, sort_keys=True).encode()).hexdigest(),
    )
    (out_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
    return manifest


class HashedSample(Protocol):
    id: str
    image_sha256: str
    graph_sha256: str


def split_hash(records: Sequence[HashedSample]) -> str:
    """The split version logged with evaluation runs (§18.1): ids + image + GT hashes."""
    lines = sorted(f"{r.id}\t{r.image_sha256}\t{r.graph_sha256}" for r in records)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def graph_hash(records: Sequence[HashedSample]) -> str:
    """Like split_hash, over ids + ground truth only: independent of the renderer."""
    lines = sorted(f"{r.id}\t{r.graph_sha256}" for r in records)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def sample_plan(config: DatasetConfig, split: SplitConfig, index: int) -> tuple[int, str, str]:
    """(level, diagram type, seed) for a sample: levels cycle fastest, then diagram types."""
    level = config.levels[index % len(config.levels)]
    diagram_type = config.diagram_types[(index // len(config.levels)) % len(config.diagram_types)]
    return level, diagram_type, f"{config.seed}:{split.name}:{index}"


def sample_graph(config: DatasetConfig, split: SplitConfig, index: int) -> GeneratedGraph:
    """A sample's ground truth, without rendering (does not depend on Graphviz)."""
    level, diagram_type, seed = sample_plan(config, split, index)
    return generate_graph(random.Random(f"{seed}:graph"), level, diagram_type)


def _make_sample(
    config: DatasetConfig, split: SplitConfig, index: int, out_dir: Path
) -> SampleRecord:
    level, diagram_type, seed = sample_plan(config, split, index)
    generated = sample_graph(config, split, index)
    last_error: Exception | None = None
    for attempt in range(1, MAX_RENDER_ATTEMPTS + 1):
        params = sample_params(
            random.Random(f"{seed}:render:{attempt}"),
            generated.graph,
            level,
            split.layouts,
            split.themes,
        )
        try:
            image = render(generated.graph, params)
            break
        except RuntimeError as exc:  # a layout engine failed; try other parameters
            last_error = exc
    else:
        raise RuntimeError(f"sample {seed} failed to render: {last_error}")

    sample_id = f"{split.name}-{index:06d}"
    graph_json = generated.graph.model_dump_json(indent=2) + "\n"
    (out_dir / "images" / f"{sample_id}.png").write_bytes(image.png)
    (out_dir / "graphs" / f"{sample_id}.json").write_text(graph_json)
    return SampleRecord(
        id=sample_id,
        split=split.name,
        seed=seed,
        level=level,
        diagram_type=diagram_type,
        image=f"images/{sample_id}.png",
        graph=f"graphs/{sample_id}.json",
        image_sha256=hashlib.sha256(image.png).hexdigest(),
        graph_sha256=hashlib.sha256(graph_json.encode()).hexdigest(),
        width=image.width,
        height=image.height,
        render_attempts=attempt,
        spec=generated.spec,
        render=params,
    )


def load_records(dataset_dir: Path, split: str | None = None) -> list[SampleRecord]:
    records = [
        SampleRecord.model_validate_json(line)
        for line in (dataset_dir / "metadata.jsonl").read_text().splitlines()
        if line.strip()
    ]
    return [r for r in records if split is None or r.split == split]
