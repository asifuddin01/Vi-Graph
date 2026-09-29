"""Training configuration: one YAML file (training/configs/), validated, logged in full."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelConfig(_Section):
    id: str
    revision: str | None = None


class DataConfig(_Section):
    dataset: str
    train_split: str = "train"
    eval_split: str = "val"
    eval_samples: int = Field(default=48, ge=0)
    image_max_side: int = Field(default=1024, ge=64)
    train_limit: int | None = Field(default=None, ge=1)


class QuantizationConfig(_Section):
    load_in_4bit: bool = True
    quant_type: Literal["nf4", "fp4"] = "nf4"
    double_quant: bool = True
    compute_dtype: Literal["float16", "bfloat16", "float32"] = "float16"


class LoraSettings(_Section):
    r: int = Field(default=16, ge=1)
    alpha: int = Field(default=32, ge=1)
    dropout: float = Field(default=0.05, ge=0.0, lt=1.0)
    target_modules: list[str]


class OptimizationConfig(_Section):
    epochs: float = Field(default=2, gt=0)
    micro_batch_size: Literal[1] = 1  # the collator handles one variable-size image at a time
    gradient_accumulation_steps: int = Field(default=16, ge=1)
    learning_rate: float = Field(default=1e-4, gt=0)
    lr_scheduler: str = "cosine"
    warmup: float = Field(default=0.03, ge=0.0, lt=1.0)
    weight_decay: float = Field(default=0.0, ge=0.0)
    max_grad_norm: float = Field(default=1.0, gt=0)
    optimizer: str = "paged_adamw_8bit"
    max_steps: int | None = Field(default=None, ge=1)  # overrides epochs (smoke run)


class CheckpointConfig(_Section):
    save_steps: int = Field(default=20, ge=1)
    save_total_limit: int = Field(default=3, ge=1)
    eval_steps: int = Field(default=40, ge=1)
    logging_steps: int = Field(default=5, ge=1)


class TrainConfig(_Section):
    run_name: str
    seed: int = 0
    model: ModelConfig
    data: DataConfig
    quantization: QuantizationConfig = QuantizationConfig()
    lora: LoraSettings
    optimization: OptimizationConfig = OptimizationConfig()
    checkpointing: CheckpointConfig = CheckpointConfig()


def load_config(path: Path, **overrides: object) -> TrainConfig:
    """Read a YAML config; ``overrides`` use dotted keys, e.g. ``{"data.train_limit": 8}``."""
    raw = yaml.safe_load(path.read_text())
    for dotted, value in overrides.items():
        section = raw
        *parents, leaf = dotted.split(".")
        for key in parents:
            section = section.setdefault(key, {})
        section[leaf] = value
    return TrainConfig.model_validate(raw)
