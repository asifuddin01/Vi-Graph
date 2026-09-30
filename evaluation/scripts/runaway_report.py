"""Why did generations hit max_new_tokens? Per level, per run (Phase 7 finding).

    PYTHONPATH=backend:. python evaluation/scripts/runaway_report.py \\
        evaluation/reports/qwen3vl-2b-qlora-a6000-v1-tok4096-s0 [more run dirs …]

Each first attempt that stopped at the token limit is classified from its raw text:

- ``stuck_in_nodes``: the "edges" list was never reached — the model kept listing (new,
  mostly invented) nodes until the budget ran out;
- ``repeating_edges``: more duplicate edges than the ground truth has edges (a loop);
- ``excess_edges``: more than twice the ground truth's edge count, without exact repeats;
- ``other``: long but none of the above.

These are "runaway enumeration" failures: with 2048 → 4096 tokens the fine-tuned model's
L4 truncations stayed at 11/28, so the budget was not the bottleneck.

Ground truth is regenerated from the generator (it does not depend on Graphviz or on a
local copy of the dataset) and must reproduce the run's split graph hash.
"""

from __future__ import annotations

import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from app.schemas import DiagramGraph
from data.generator.dataset import default_config, graph_hash, sample_graph
from evaluation.results import RunInfo, SampleResult, read_results, read_run

EDGE = re.compile(r'"source":\s*"([^"]+)",\s*"target":\s*"([^"]+)"')
CLASSES = ("stuck_in_nodes", "repeating_edges", "excess_edges", "other")


def classify(text: str, ground_truth: DiagramGraph) -> str:
    if '"edges"' not in text:
        return "stuck_in_nodes"
    edges = EDGE.findall(text)
    if len(edges) - len(set(edges)) > len(ground_truth.edges):
        return "repeating_edges"
    if len(edges) > 2 * len(ground_truth.edges):
        return "excess_edges"
    return "other"


class _Hashed:
    def __init__(self, sample_id: str, graph: DiagramGraph) -> None:
        self.id = sample_id
        json_text = graph.model_dump_json(indent=2) + "\n"  # as the dataset builder writes it
        self.graph_sha256 = hashlib.sha256(json_text.encode()).hexdigest()


def ground_truth(run: RunInfo) -> dict[str, DiagramGraph]:
    """The run's split, regenerated; refuses if it isn't the split the run was scored on."""
    config = default_config(run.split.dataset)
    split = next(s for s in config.splits if s.name == run.split.split)
    graphs = {
        f"{split.name}-{i:06d}": sample_graph(config, split, i).graph for i in range(split.size)
    }
    regenerated = graph_hash([_Hashed(sample_id, g) for sample_id, g in graphs.items()])
    if regenerated != run.split.graph_hash:
        raise SystemExit(f"{run.name}: regenerated ground truth does not match the run's split")
    return graphs


def runaway_by_level(
    results: list[SampleResult], graphs: dict[str, DiagramGraph]
) -> dict[int, Counter]:
    """Per level: samples, truncated first attempts by class, and failed samples."""
    table: dict[int, Counter] = defaultdict(Counter)
    for result in results:
        counts = table[int(result.attributes["level"])]
        counts["samples"] += 1
        counts["failed"] += not result.scores.has_graph
        analysis = result.prediction.analysis
        if analysis is None:
            continue
        first = analysis.extraction.attempts[0].output
        if first.finish_reason != "length":
            continue
        counts["truncated"] += 1
        counts[classify(first.text, graphs[result.sample_id])] += 1
    return dict(sorted(table.items()))


def main(argv: list[str]) -> int:
    for run_dir in map(Path, argv):
        run = read_run(run_dir)
        print(f"\n{run.name} (max_new_tokens {run.config.max_new_tokens})")
        for level, c in runaway_by_level(read_results(run_dir), ground_truth(run)).items():
            kinds = ", ".join(f"{k} {c[k]}" for k in CLASSES)
            print(
                f"  L{level}: {c['truncated']}/{c['samples']} truncated ({kinds}); "
                f"{c['failed']} failed"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
