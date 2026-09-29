import json
import re
from pathlib import Path

import pytest

from app.exporters.graphviz import graphviz_available
from app.schemas import DiagramGraph
from app.vlm.prompts import GRAPH_EXTRACTION
from data.generator.dataset import build_dataset, default_config
from training.qlora.collate import (
    IGNORE_INDEX,
    Collator,
    LabelMaskError,
    assistant_header,
    flat_ids,
    mask_prompt,
)
from training.qlora.config import TrainConfig, load_config
from training.qlora.data import (
    Example,
    ExampleDataset,
    HeldOutSplitError,
    build_example,
    load_training_split,
    training_target,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "training" / "configs" / "qlora_t4.yaml"
EXAMPLE = ROOT / "examples" / "outputs" / "L3-system-architecture-layered-lr-corporate.json"
needs_graphviz = pytest.mark.skipif(not graphviz_available(), reason="Graphviz not installed")


# --- config ---------------------------------------------------------------------------


def test_the_committed_config_is_valid() -> None:
    config = load_config(CONFIG)

    assert isinstance(config, TrainConfig)
    assert config.quantization.compute_dtype == "float16"  # T4: no bf16
    assert config.optimization.micro_batch_size == 1
    assert config.data.train_split == "train" and config.data.eval_split == "val"
    assert "q_proj" in config.lora.target_modules and "qkv" not in config.lora.target_modules


def test_config_overrides_use_dotted_keys() -> None:
    config = load_config(CONFIG, **{"data.train_limit": 8, "optimization.max_steps": 2, "seed": 3})

    assert (config.data.train_limit, config.optimization.max_steps, config.seed) == (8, 2, 3)


def test_config_rejects_unknown_keys_and_bad_values() -> None:
    with pytest.raises(ValueError):
        load_config(CONFIG, **{"lora.rank": 8})
    with pytest.raises(ValueError):
        load_config(CONFIG, **{"optimization.micro_batch_size": 4})


# --- targets --------------------------------------------------------------------------


def test_target_is_compact_schema_valid_json_without_nulls() -> None:
    graph = DiagramGraph.model_validate_json(EXAMPLE.read_text())

    target = training_target(graph)

    assert DiagramGraph.model_validate_json(target) == graph
    assert "null" not in target and ": " not in target and "\n" not in target
    assert json.loads(target)["schema_version"] == "2.0"
    assert len(target) < len(EXAMPLE.read_text())


def test_target_keeps_unicode_labels_readable() -> None:
    graph = DiagramGraph.model_validate(
        {
            "schema_version": "2.0",
            "diagram_type": "flowchart",
            "nodes": [{"id": "n1", "label": "Größe → μ", "type": "module"}],
            "edges": [],
        }
    )

    assert "Größe → μ" in training_target(graph)


# --- label masking --------------------------------------------------------------------


def test_mask_prompt_masks_through_the_last_header() -> None:
    header = [1, 2]
    ids = [9, 1, 2, 5, 1, 2, 7, 8, 3]  # the header appears twice; the answer follows the last

    assert mask_prompt(ids, header) == [IGNORE_INDEX] * 6 + [7, 8, 3]


def test_mask_prompt_errors() -> None:
    with pytest.raises(LabelMaskError, match="not found"):
        mask_prompt([5, 6, 7], [1, 2])
    with pytest.raises(LabelMaskError, match="nothing after"):
        mask_prompt([5, 1, 2], [1, 2])


def test_flat_ids_accepts_batched_and_flat_input() -> None:
    assert flat_ids([[1, 2, 3]]) == [1, 2, 3]
    assert flat_ids([1, 2, 3]) == [1, 2, 3]
    with pytest.raises(ValueError):
        flat_ids([[1], [2]])


class FakeTokenizer:
    """Whole words and special tokens → ids, like a tokenizer would, deterministically."""

    TOKEN = re.compile(r"<\|[a-z_]+\|>|\n|[^\s<]+|\s+")

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}

    def __call__(self, text: str, add_special_tokens: bool = False) -> dict[str, list[int]]:
        return {
            "input_ids": [
                self.vocab.setdefault(t, len(self.vocab)) for t in self.TOKEN.findall(text)
            ]
        }

    def decode(self, ids: list[int]) -> str:
        inverse = {v: k for k, v in self.vocab.items()}
        return "".join(inverse[i] for i in ids)


class FakeProcessor:
    """A Qwen-style chat template: <|im_start|>role\\n…<|im_end|>\\n; images → pad tokens."""

    def __init__(self) -> None:
        self.tokenizer = FakeTokenizer()

    def apply_chat_template(
        self, conversation, add_generation_prompt=False, tokenize=False, return_dict=False, **_
    ):
        text = ""
        for message in conversation:
            parts = []
            for item in message["content"]:
                parts.append(
                    "<|image_pad|><|image_pad|>" if item["type"] == "image" else item["text"]
                )
            text += f"<|im_start|>{message['role']}\n{''.join(parts)}<|im_end|>\n"
        if add_generation_prompt:
            text += "<|im_start|>assistant\n"
        if not tokenize:
            return text
        ids = self.tokenizer(text)["input_ids"]
        return {"input_ids": [ids]} if return_dict else [ids]


def test_assistant_header_comes_from_the_template() -> None:
    processor = FakeProcessor()

    header = assistant_header(processor)

    assert processor.tokenizer.decode(header) == "<|im_start|>assistant\n"


def test_trained_text_is_exactly_the_answer_and_end_of_turn(tmp_path: Path) -> None:
    graph = DiagramGraph.model_validate_json(EXAMPLE.read_text())
    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": None},
                {"type": "text", "text": GRAPH_EXTRACTION.text},
            ],
        },
        {"role": "assistant", "content": [{"type": "text", "text": training_target(graph)}]},
    ]
    collator = Collator(FakeProcessor())

    trained = collator.trained_text(Example("s", conversation))

    assert trained == training_target(graph) + "<|im_end|>\n"


# --- examples from a real dataset -----------------------------------------------------


@pytest.fixture(scope="module")
def dataset(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not graphviz_available():
        pytest.skip("Graphviz not installed")
    out = tmp_path_factory.mktemp("train-data")
    build_dataset(default_config("tiny", seed=6, train=4, val=2, test=2), out)
    return out


def test_examples_use_the_inference_prompt_and_stage_a(dataset: Path) -> None:
    _, samples = load_training_split(dataset, "train")

    example = build_example(samples[0], image_max_side=256)

    user, assistant = example.conversation
    assert user["role"] == "user" and assistant["role"] == "assistant"
    image, prompt = user["content"]
    assert image["type"] == "image" and max(image["image"].size) <= 256
    assert prompt == {"type": "text", "text": GRAPH_EXTRACTION.text}
    graph = DiagramGraph.model_validate_json(samples[0].graph.read_text())
    assert assistant["content"][0]["text"] == training_target(graph)


def test_dataset_is_lazy_and_sized(dataset: Path) -> None:
    _, samples = load_training_split(dataset, "train", limit=3)

    examples = ExampleDataset(samples, image_max_side=512)

    assert len(examples) == 3 and examples[2].sample_id == "train-000002"


def test_never_trains_on_the_held_out_test_split(dataset: Path) -> None:
    with pytest.raises(HeldOutSplitError):
        load_training_split(dataset, "test")
    info, samples = load_training_split(dataset, "val")
    assert info.split == "val" and len(samples) == 2
