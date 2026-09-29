"""Training examples: exactly the inference conversation, with the ground truth as answer.

The user turn is what the app sends at inference — Stage A preprocessing (same
``image_max_side``) and the ``graph_extraction@1`` prompt via ``build_extraction_messages``
and the HF backend's ``to_chat_messages`` — so the adapter learns the deployed format.
The answer is the ground-truth graph as compact JSON with nulls omitted (schema-valid; the
prompt's "… or null" fields are optional), which saves ~25% of target tokens on a T4.

Held-out splits (manifest ``held_out``) are refused: never train on the test set.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.schemas import DiagramGraph
from app.utils.images import preprocess_image
from app.vlm.hf import to_chat_messages
from app.vlm.prompts import GRAPH_EXTRACTION, build_extraction_messages
from evaluation.samples import EvalSample, SplitInfo, load_split

IMAGE_MAX_PIXELS = 40_000_000  # the app default (VIGRAPH_IMAGE_MAX_PIXELS)


class HeldOutSplitError(ValueError):
    pass


def training_target(graph: DiagramGraph) -> str:
    """The answer the model learns: compact JSON, nulls omitted."""
    return json.dumps(
        graph.model_dump(mode="json", exclude_none=True), ensure_ascii=False, separators=(",", ":")
    )


@dataclass
class Example:
    sample_id: str
    conversation: list[dict[str, Any]]  # user (image + prompt), assistant (target)


def build_example(sample: EvalSample, image_max_side: int) -> Example:
    prepared = preprocess_image(
        sample.image.read_bytes(), max_side=image_max_side, max_pixels=IMAGE_MAX_PIXELS
    )
    graph = DiagramGraph.model_validate_json(sample.graph.read_text())
    conversation = to_chat_messages(build_extraction_messages([prepared.image]))
    conversation.append(
        {"role": "assistant", "content": [{"type": "text", "text": training_target(graph)}]}
    )
    return Example(sample.id, conversation)


class ExampleDataset:
    """Map-style dataset (the torch Dataset protocol); images are loaded on access."""

    def __init__(self, samples: list[EvalSample], image_max_side: int) -> None:
        self.samples = samples
        self.image_max_side = image_max_side

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> Example:
        return build_example(self.samples[index], self.image_max_side)


def load_training_split(
    dataset_dir: Path, split: str, *, limit: int | None = None
) -> tuple[SplitInfo, list[EvalSample]]:
    """A verified split for training or validation; refuses held-out (test) splits."""
    manifest = json.loads((dataset_dir / "manifest.json").read_text())
    for entry in manifest["config"]["splits"]:
        if entry["name"] == split and entry.get("held_out"):
            raise HeldOutSplitError(f"split {split!r} is held out: never train on it")
    info, samples = load_split(dataset_dir, split)
    return info, samples[:limit] if limit else samples


def prompt_metadata() -> dict[str, str]:
    return {"prompt_id": GRAPH_EXTRACTION.id, "prompt_sha256": GRAPH_EXTRACTION.sha256}
