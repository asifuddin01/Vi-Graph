"""Evaluation CLI (run from the repo root with backend/ on PYTHONPATH).

    PYTHONPATH=backend python -m evaluation run --dataset data/synthetic/synthetic-v1 \\
        --split test --backend hf --dtype float16 --out evaluation/reports/zero-shot-seed0
    PYTHONPATH=backend python -m evaluation summarize evaluation/reports/zero-shot-seed0
    PYTHONPATH=backend python -m evaluation rescore evaluation/reports/zero-shot-seed0

``run`` resumes when pointed at an unfinished run directory with the same arguments.
``--backend oracle`` answers with the ground truth — a sanity check of the evaluation path
(every score must be perfect), never a result. ``--backend mock`` returns the spec example.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import Settings
from app.vlm.base import DecodingParams
from app.vlm.factory import create_vlm_backend
from evaluation.predictors import OraclePredictor, Predictor, VLMPredictor
from evaluation.report import fmt
from evaluation.results import RunConfig, read_results, read_run
from evaluation.runner import finalize, rescore, run_evaluation
from evaluation.samples import SplitInfo, load_split


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m evaluation")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="evaluate a model on a dataset split")
    run.add_argument("--dataset", type=Path, required=True)
    run.add_argument("--split", default="test")
    run.add_argument("--out", type=Path, required=True, help="run directory (resumable)")
    run.add_argument("--name", help="run name (default: the directory name)")
    run.add_argument("--limit", type=int, help="only the first N samples (stratified prefix)")
    run.add_argument("--backend", choices=["hf", "mock", "oracle"], default="hf")
    defaults = Settings()
    run.add_argument("--model-id", default=defaults.vlm_model_id)
    run.add_argument("--revision", default=defaults.vlm_revision)
    run.add_argument("--adapter", type=Path, help="LoRA adapter directory")
    run.add_argument("--dtype", default=defaults.vlm_dtype)
    run.add_argument("--device-map", default=defaults.vlm_device_map)
    decoding = DecodingParams()
    run.add_argument("--temperature", type=float, default=decoding.temperature)
    run.add_argument("--top-p", type=float, default=decoding.top_p)
    run.add_argument("--max-new-tokens", type=int, default=decoding.max_new_tokens)
    run.add_argument("--seed", type=int, default=decoding.seed)
    run.add_argument("--image-max-side", type=int, default=defaults.image_max_side)
    run.add_argument("--image-max-pixels", type=int, default=defaults.image_max_pixels)
    run.add_argument("--retry-errors", action="store_true", help="re-run samples that raised")
    run.add_argument("--max-consecutive-errors", type=int, default=3)
    run.add_argument("--quiet", action="store_true")

    summarize = commands.add_parser("summarize", help="rewrite summary.json and report.md")
    summarize.add_argument("run_dir", type=Path)

    rescore_cmd = commands.add_parser("rescore", help="re-score stored predictions (no model)")
    rescore_cmd.add_argument("run_dir", type=Path)

    args = parser.parse_args(argv)
    if args.command == "run":
        summary = _run(args, sys.argv if argv is None else ["python -m evaluation", *argv])
    elif args.command == "summarize":
        summary = finalize(args.run_dir, read_run(args.run_dir), read_results(args.run_dir))
    else:
        run_info = read_run(args.run_dir)
        _, samples = load_split(Path(run_info.split.directory), run_info.split.split)
        summary = rescore(args.run_dir, samples[: run_info.config.limit])
    _print_headline(summary)
    return 0


def _run(args: argparse.Namespace, command: list[str]) -> dict[str, object]:
    split, samples = load_split(args.dataset, args.split)
    samples = samples[: args.limit] if args.limit else samples
    params = DecodingParams(
        temperature=args.temperature,
        top_p=args.top_p,
        max_new_tokens=args.max_new_tokens,
        seed=args.seed,
    )
    uses_model = args.backend == "hf"
    config = RunConfig(
        dataset=str(args.dataset.resolve()),
        split=args.split,
        limit=args.limit,
        predictor="oracle" if args.backend == "oracle" else f"vlm:{args.backend}",
        model_id=args.model_id if uses_model else None,
        revision=args.revision if uses_model else None,
        adapter=str(args.adapter) if uses_model and args.adapter else None,
        dtype=args.dtype if uses_model else None,
        temperature=params.temperature,
        top_p=params.top_p,
        max_new_tokens=params.max_new_tokens,
        seed=params.seed,
        image_max_side=args.image_max_side,
        image_max_pixels=args.image_max_pixels,
    )
    predictor = _predictor(args, params, split)
    return run_evaluation(
        predictor,
        samples,
        split,
        config,
        args.out,
        name=args.name,
        command=command,
        retry_errors=args.retry_errors,
        max_consecutive_errors=args.max_consecutive_errors,
        adapter_config=_adapter_config(args.adapter) if uses_model else None,
        progress=not args.quiet,
    )


def _predictor(args: argparse.Namespace, params: DecodingParams, split: SplitInfo) -> Predictor:
    limits = {
        "image_max_side": args.image_max_side,
        "image_max_pixels": args.image_max_pixels,
        "split_version": split.split_hash,
    }
    if args.backend == "oracle":
        return OraclePredictor(params, **limits)
    settings = Settings(
        vlm_backend=args.backend,
        vlm_model_id=args.model_id,
        vlm_revision=args.revision,
        vlm_adapter_path=args.adapter,
        vlm_dtype=args.dtype,
        vlm_device_map=args.device_map,
    )
    return VLMPredictor(create_vlm_backend(settings), params, **limits)


def _adapter_config(adapter: Path | None) -> dict[str, object] | None:
    """LoRA settings for §18.1 (rank, alpha, target modules), from PEFT's adapter_config."""
    if adapter is None or not (adapter / "adapter_config.json").exists():
        return None
    raw = json.loads((adapter / "adapter_config.json").read_text())
    keys = (
        "base_model_name_or_path",
        "peft_type",
        "r",
        "lora_alpha",
        "lora_dropout",
        "target_modules",
    )
    return {k: raw.get(k) for k in keys}


def _print_headline(summary: dict) -> None:
    macro = summary["macro"]
    print(
        f"{summary['samples']} samples · node F1 {fmt(macro['node_f1']['mean'])} · edge F1 "
        f"{fmt(macro['edge_f1']['mean'])} · graph similarity "
        f"{fmt(macro['graph_similarity']['mean'])} · QA {fmt(macro['qa_accuracy']['mean'])} · "
        f"valid post-repair {fmt(macro['valid_post_repair']['mean'])}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
