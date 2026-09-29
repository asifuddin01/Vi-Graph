"""Synthetic dataset CLI (run from the repo root with backend/ on PYTHONPATH).

    PYTHONPATH=backend python -m data.generator build --out data/synthetic/synthetic-v1
    PYTHONPATH=backend python -m data.generator verify data/synthetic/synthetic-v1
    PYTHONPATH=backend python -m data.generator stats data/synthetic/synthetic-v1

``build`` defaults to the spec §32 sizes (2000 train / 300 val / 500 held-out test).
``verify`` re-hashes every file against metadata.jsonl and manifest.json and re-validates
every ground-truth graph — run it before training or evaluating on a copied dataset. With
``--reference data/splits/synthetic-v1.manifest.json`` it also checks that the ground truth
equals the committed build (images may differ across Graphviz versions; graphs may not).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

from app.schemas import DiagramGraph
from data.generator.dataset import (
    Manifest,
    build_dataset,
    default_config,
    graph_hash,
    load_records,
    split_hash,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m data.generator")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="generate a dataset")
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--name", default="synthetic-v1")
    build.add_argument("--seed", type=int, default=0)
    build.add_argument("--train", type=int, default=2000)
    build.add_argument("--val", type=int, default=300)
    build.add_argument("--test", type=int, default=500)
    build.add_argument("--iid-test", type=int, default=0, help="in-distribution test samples")
    build.add_argument("--workers", type=int, default=4)
    build.add_argument("--overwrite", action="store_true")

    verify = commands.add_parser("verify", help="check a dataset's files against its manifest")
    verify.add_argument("dir", type=Path)
    verify.add_argument(
        "--reference", type=Path, help="manifest whose ground truth this build must reproduce"
    )

    stats = commands.add_parser("stats", help="summarize a dataset (for data cards / the paper)")
    stats.add_argument("dir", type=Path)

    args = parser.parse_args(argv)
    if args.command == "build":
        config = default_config(
            args.name,
            seed=args.seed,
            train=args.train,
            val=args.val,
            test=args.test,
            iid_test=args.iid_test,
        )
        start = time.perf_counter()
        manifest = build_dataset(config, args.out, workers=args.workers, overwrite=args.overwrite)
        print(f"built {manifest.name} in {time.perf_counter() - start:.0f}s: {manifest.counts}")
        print(f"dataset hash {manifest.dataset_hash}")
        return 0
    if args.command == "stats":
        print(json.dumps(dataset_stats(args.dir), indent=2))
        return 0
    return verify_dataset(args.dir, args.reference)


def dataset_stats(directory: Path) -> dict[str, object]:
    records = load_records(directory)
    by_split: dict[str, list] = {}
    for record in records:
        by_split.setdefault(record.split, []).append(record)

    def mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0.0

    summary: dict[str, object] = {}
    for split, members in by_split.items():
        levels = sorted({r.level for r in members})
        summary[split] = {
            "samples": len(members),
            "levels": {
                f"L{level}": {
                    "samples": sum(r.level == level for r in members),
                    "mean_nodes": mean([r.spec.n_nodes for r in members if r.level == level]),
                    "mean_edges": mean([r.spec.n_edges for r in members if r.level == level]),
                    "cyclic": sum(r.spec.has_cycle for r in members if r.level == level),
                    "with_groups": sum(r.spec.n_groups > 0 for r in members if r.level == level),
                }
                for level in levels
            },
            "diagram_types": dict(Counter(r.diagram_type for r in members).most_common()),
            "layouts": dict(Counter(r.render.layout for r in members).most_common()),
            "themes": dict(Counter(r.render.theme for r in members).most_common()),
            "patterns": dict(Counter(p for r in members for p in r.spec.patterns).most_common()),
            "mean_image_size": [
                mean([r.width for r in members]),
                mean([r.height for r in members]),
            ],
        }
    return summary


def verify_dataset(directory: Path, reference: Path | None = None) -> int:
    manifest = Manifest.model_validate_json((directory / "manifest.json").read_text())
    records = load_records(directory)
    problems: list[str] = []
    for record in records:
        image = (directory / record.image).read_bytes()
        graph = (directory / record.graph).read_bytes()
        if hashlib.sha256(image).hexdigest() != record.image_sha256:
            problems.append(f"{record.id}: image hash mismatch")
        if hashlib.sha256(graph).hexdigest() != record.graph_sha256:
            problems.append(f"{record.id}: graph hash mismatch")
        DiagramGraph.model_validate_json(graph)
    for split, expected in manifest.split_hashes.items():
        members = [r for r in records if r.split == split]
        listed = (directory / "splits" / f"{split}.txt").read_text().split()
        if listed != [r.id for r in members]:
            problems.append(f"split {split}: splits/{split}.txt does not match metadata")
        if split_hash(members) != expected:
            problems.append(f"split {split}: hash mismatch")
        if graph_hash(members) != manifest.graph_hashes.get(split):
            problems.append(f"split {split}: ground-truth hash mismatch")
    if reference is not None:
        expected_graphs = Manifest.model_validate_json(reference.read_text()).graph_hashes
        if manifest.graph_hashes != expected_graphs:
            problems.append(f"ground truth differs from {reference}")
    for problem in problems:
        print(problem, file=sys.stderr)
    print(
        f"{len(records)} samples checked; {'OK' if not problems else f'{len(problems)} problems'}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
