"""QLoRA fine-tuning on a Colab T4 (spec §18). Called from the training notebook.

Needs requirements-train.txt and a CUDA GPU; torch/transformers/peft are imported inside
``run_training`` so the rest of this module (and its tests) work without them.

Layout of a run directory (put it on Google Drive):

    run_config.json      config + data fingerprint; a resumed run must match it exactly
    checkpoints/         Trainer checkpoints (resume after a disconnect)
    train_log.jsonl      every logged step (loss, lr, grad norm, eval loss)
    adapter/             the trained LoRA adapter (adapter_config.json + weights)
    training_run.json    §18.1 metadata: model + revision, LoRA, quantization, prompt hash,
                         seed, schema version, split hashes, hyperparameters, versions, timings

Calling ``run_training`` again with the same arguments resumes from the latest checkpoint.
"""

from __future__ import annotations

import contextlib
import json
import math
import platform
import subprocess
import time
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.schemas import SCHEMA_VERSION
from evaluation.samples import SplitInfo
from training.qlora.collate import Collator
from training.qlora.config import TrainConfig
from training.qlora.data import ExampleDataset, load_training_split, prompt_metadata

RUN_CONFIG = "run_config.json"
TRAIN_LOG = "train_log.jsonl"
TRAINING_RUN = "training_run.json"
PACKAGES = ("torch", "transformers", "peft", "bitsandbytes", "accelerate", "pillow")


class ResumeMismatch(ValueError):
    pass


class TrainingResult(BaseModel):
    adapter_dir: str
    metadata_path: str
    train_loss: float | None
    eval_loss: float | None
    seconds: float


def fingerprint(config: TrainConfig, train: SplitInfo, evaluation: SplitInfo) -> dict[str, Any]:
    return {
        "config": config.model_dump(mode="json"),
        "train_split": train.model_dump(mode="json", exclude={"directory"}),
        "eval_split": evaluation.model_dump(mode="json", exclude={"directory"}),
    }


def resume_guard(output_dir: Path, current: dict[str, Any]) -> bool:
    """Record the run's config + data on first use; on resume, require an exact match.
    Returns True when resuming an existing run."""
    path = output_dir / RUN_CONFIG
    if not path.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, indent=2) + "\n")
        return False
    stored = json.loads(path.read_text())
    if stored != current:
        differing = sorted(k for k in current if stored.get(k) != current.get(k))
        raise ResumeMismatch(
            f"{output_dir} holds a run with a different {', '.join(differing)}; "
            "use a new output directory (or run_name) for a new run"
        )
    return True


def projected_hours(seconds_per_sample: float, samples: int, epochs: float) -> float:
    return seconds_per_sample * samples * epochs / 3600


def total_steps(samples: int, epochs: float, accumulation: int, max_steps: int | None) -> int:
    if max_steps:
        return max_steps
    return math.ceil(math.ceil(samples / accumulation) * epochs)


def run_training(config: TrainConfig, dataset_dir: Path, output_dir: Path) -> TrainingResult:
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForImageTextToText,
        AutoProcessor,
        BitsAndBytesConfig,
        Trainer,
        TrainerCallback,
        TrainingArguments,
        set_seed,
    )
    from transformers.trainer_utils import get_last_checkpoint

    started = time.perf_counter()
    train_info, train_samples = load_training_split(
        dataset_dir, config.data.train_split, limit=config.data.train_limit
    )
    eval_info, eval_samples = load_training_split(
        dataset_dir, config.data.eval_split, limit=config.data.eval_samples or None
    )
    resuming = resume_guard(output_dir, fingerprint(config, train_info, eval_info))

    set_seed(config.seed)
    compute_dtype = getattr(torch, config.quantization.compute_dtype)
    processor = AutoProcessor.from_pretrained(config.model.id, revision=config.model.revision)
    model = AutoModelForImageTextToText.from_pretrained(
        config.model.id,
        revision=config.model.revision,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=config.quantization.load_in_4bit,
            bnb_4bit_quant_type=config.quantization.quant_type,
            bnb_4bit_use_double_quant=config.quantization.double_quant,
            bnb_4bit_compute_dtype=compute_dtype,
        ),
        dtype=compute_dtype,
        device_map={"": 0},
    )
    revision = getattr(model.config, "_commit_hash", None) or config.model.revision
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    for cfg in (model.config, getattr(model.config, "text_config", None)):
        if cfg is not None:
            cfg.use_cache = False  # incompatible with gradient checkpointing
    lora = LoraConfig(
        r=config.lora.r,
        lora_alpha=config.lora.alpha,
        lora_dropout=config.lora.dropout,
        target_modules=config.lora.target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    trainable, total = model.get_nb_trainable_parameters()

    log_path = output_dir / TRAIN_LOG

    class JsonlLog(TrainerCallback):
        def on_log(
            self, args: Any, state: Any, control: Any, logs: Any = None, **kwargs: Any
        ) -> None:
            entry = {"step": state.global_step, "epoch": state.epoch, **(logs or {})}
            entry["time"] = datetime.now(UTC).isoformat()
            with log_path.open("a") as handle:
                handle.write(json.dumps(entry) + "\n")

    opt, ckpt = config.optimization, config.checkpointing
    args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        per_device_train_batch_size=opt.micro_batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=opt.gradient_accumulation_steps,
        num_train_epochs=opt.epochs,
        max_steps=opt.max_steps or -1,
        learning_rate=opt.learning_rate,
        lr_scheduler_type=opt.lr_scheduler,
        warmup_steps=opt.warmup,  # a float in [0, 1) is a ratio of the total steps
        weight_decay=opt.weight_decay,
        max_grad_norm=opt.max_grad_norm,
        optim=opt.optimizer,
        fp16=config.quantization.compute_dtype == "float16",
        bf16=config.quantization.compute_dtype == "bfloat16",
        logging_steps=ckpt.logging_steps,
        save_strategy="steps",
        save_steps=ckpt.save_steps,
        save_total_limit=ckpt.save_total_limit,
        eval_strategy="steps" if eval_samples else "no",
        eval_steps=ckpt.eval_steps,
        remove_unused_columns=False,  # the dataset yields Examples; the collator tokenizes
        report_to="none",
        seed=config.seed,
        data_seed=config.seed,
        dataloader_num_workers=2,
    )
    collator = Collator(processor)
    trainer = Trainer(
        model=model,
        args=args,
        data_collator=collator,
        train_dataset=ExampleDataset(train_samples, config.data.image_max_side),
        eval_dataset=ExampleDataset(eval_samples, config.data.image_max_side)
        if eval_samples
        else None,
        callbacks=[JsonlLog()],
    )
    checkpoints = output_dir / "checkpoints"
    last = get_last_checkpoint(str(checkpoints)) if checkpoints.exists() else None
    output = trainer.train(resume_from_checkpoint=last)
    eval_loss = trainer.evaluate()["eval_loss"] if eval_samples else None

    adapter_dir = output_dir / "adapter"
    model.save_pretrained(str(adapter_dir))
    seconds = time.perf_counter() - started
    metadata = {
        "run_name": config.run_name,
        "completed_at": datetime.now(UTC).isoformat(),
        "resumed": resuming or last is not None,
        "resumed_from": last,
        "model": {"id": config.model.id, "revision": revision},
        "lora": config.lora.model_dump(),
        "quantization": config.quantization.model_dump(),
        "trainable_parameters": trainable,
        "total_parameters": total,
        **prompt_metadata(),
        "target_format": "compact JSON, nulls omitted (training/qlora/data.py)",
        "seed": config.seed,
        "schema_version": SCHEMA_VERSION,
        "image_max_side": config.data.image_max_side,
        "train_split": train_info.model_dump(mode="json"),
        "eval_split": eval_info.model_dump(mode="json"),
        "train_samples": len(train_samples),
        "eval_samples": len(eval_samples),
        "config": config.model_dump(mode="json"),
        "global_steps": trainer.state.global_step,
        "train_loss": output.training_loss,
        "eval_loss": eval_loss,
        "seconds_this_session": seconds,
        "peak_gpu_memory_gb": torch.cuda.max_memory_allocated() / 1024**3,
        "environment": environment(),
    }
    metadata_path = output_dir / TRAINING_RUN
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str) + "\n")
    return TrainingResult(
        adapter_dir=str(adapter_dir),
        metadata_path=str(metadata_path),
        train_loss=output.training_loss,
        eval_loss=eval_loss,
        seconds=seconds,
    )


def environment() -> dict[str, Any]:
    packages = {}
    for package in PACKAGES:
        with contextlib.suppress(PackageNotFoundError):
            packages[package] = version(package)
    info: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "git_commit": _git_commit(),
    }
    try:
        import torch

        info["torch_cuda"] = torch.version.cuda
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
            info["gpu_memory_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1024**3, 1
            )
    except ImportError:
        pass
    return info


def _git_commit() -> str | None:
    try:
        root = Path(__file__).resolve().parents[2]
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
