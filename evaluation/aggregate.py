"""Aggregate per-sample results into a run summary.

Two kinds of numbers:

- **Macro** (the headline): the mean over samples of a per-sample metric
  (``SAMPLE_METRICS``). Every sample counts equally, failed predictions included (they
  score 0); metrics undefined for a sample (e.g. label accuracy with nothing matched) skip
  it, and ``n`` says how many samples were averaged. Per-sample values are also what the
  paired significance tests compare (§20.11).
- **Pooled** (micro): counts summed over the run before dividing — node/edge P/R/F1 over all
  nodes and edges, label accuracy over all matched labels, QA accuracy over all questions.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from collections.abc import Callable

from evaluation.metrics.errors import ErrorCounts
from evaluation.metrics.matching import prf
from evaluation.metrics.structural_qa import QUESTION_KINDS
from evaluation.results import SampleResult
from evaluation.samples import BREAKDOWNS

MetricFn = Callable[[SampleResult], float | None]


def _qa_accuracy(r: SampleResult) -> float | None:
    return sum(o.correct for o in r.qa) / len(r.qa) if r.qa else None


def _label_accuracy(r: SampleResult) -> float | None:
    labels = r.scores.labels
    return labels.exact / labels.matched if labels and labels.matched else None


def _validity(field: str) -> MetricFn:
    def metric(r: SampleResult) -> float | None:
        v = r.prediction.validity
        return float(getattr(v, field)) if v is not None else None

    return metric


SAMPLE_METRICS: dict[str, MetricFn] = {
    "node_f1": lambda r: r.scores.nodes.f1,
    "node_precision": lambda r: r.scores.nodes.precision,
    "node_recall": lambda r: r.scores.nodes.recall,
    "edge_f1": lambda r: r.scores.edges.f1,
    "edge_precision": lambda r: r.scores.edges.precision,
    "edge_recall": lambda r: r.scores.edges.recall,
    "edge_strict_f1": lambda r: r.scores.edges_strict.f1,
    "graph_similarity": lambda r: r.scores.graph_similarity,
    "label_accuracy": _label_accuracy,
    "diagram_type_accuracy": lambda r: float(r.scores.diagram_type_correct),
    "qa_accuracy": _qa_accuracy,
    "valid_first_attempt": _validity("first_attempt"),
    "valid_bare_json": _validity("first_attempt_bare_json"),
    "valid_post_repair": lambda r: float(r.scores.has_graph),
    "first_attempt_node_f1": lambda r: r.first_attempt_scores.nodes.f1,
    "first_attempt_edge_f1": lambda r: r.first_attempt_scores.edges.f1,
    "first_attempt_graph_similarity": lambda r: r.first_attempt_scores.graph_similarity,
    "latency_ms": lambda r: r.prediction.latency_ms,
}

# Shown per level / diagram type / layout / theme.
BREAKDOWN_METRICS = (
    "node_f1",
    "edge_f1",
    "edge_strict_f1",
    "graph_similarity",
    "label_accuracy",
    "qa_accuracy",
    "valid_post_repair",
    "diagram_type_accuracy",
)


def macro(results: list[SampleResult], metric: str) -> dict[str, float | int | None]:
    values = [v for r in results if (v := SAMPLE_METRICS[metric](r)) is not None]
    return {
        "mean": statistics.fmean(values) if values else None,
        "std": statistics.stdev(values) if len(values) > 1 else None,
        "n": len(values),
    }


def summarize(results: list[SampleResult]) -> dict[str, object]:
    with_graph = [r for r in results if r.scores.has_graph]
    return {
        "samples": len(results),
        "with_graph": len(with_graph),
        "errors": sum(r.prediction.error is not None for r in results),
        "macro": {name: macro(results, name) for name in SAMPLE_METRICS},
        "pooled": _pooled(results),
        "validity": _validity_summary(results),
        "qa": _qa_summary(results),
        "errors_taxonomy": _taxonomy(with_graph),
        "latency_ms": _latency(results),
        "breakdowns": _breakdowns(results),
    }


def _pooled(results: list[SampleResult]) -> dict[str, object]:
    def pooled_prf(get: Callable[[SampleResult], object]) -> dict[str, float | int]:
        parts = [get(r) for r in results]
        return prf(
            sum(p.tp for p in parts), sum(p.fp for p in parts), sum(p.fn for p in parts)
        ).model_dump()

    labels = [r.scores.labels for r in results if r.scores.labels]
    matched = sum(x.matched for x in labels)
    chars = sum(x.chars for x in labels)
    words = sum(x.words for x in labels)
    text = [r.scores.edge_text for r in results if r.scores.edge_text]
    with_text = sum(x.matched_with_text for x in text)
    grouping = [r.scores.grouping for r in results if r.scores.grouping]
    grouped = sum(x.matched for x in grouping)
    return {
        "nodes": pooled_prf(lambda r: r.scores.nodes),
        "edges": pooled_prf(lambda r: r.scores.edges),
        "edges_strict": pooled_prf(lambda r: r.scores.edges_strict),
        "labels": {
            "matched": matched,
            "exact": sum(x.exact for x in labels) / matched if matched else None,
            "exact_casefold": sum(x.exact_casefold for x in labels) / matched if matched else None,
            "mean_similarity": sum(x.similarity_sum for x in labels) / matched if matched else None,
            "cer": sum(x.char_edits for x in labels) / chars if chars else None,
            "wer": sum(x.word_edits for x in labels) / words if words else None,
        },
        "edge_text": {
            "matched_with_text": with_text,
            "accuracy": sum(x.correct for x in text) / with_text if with_text else None,
            "lost": sum(x.lost for x in text),
            "wrong": sum(x.wrong for x in text),
            "hallucinated": sum(x.hallucinated for x in text),
        },
        "grouping": {
            "matched": grouped,
            "accuracy": sum(x.correct for x in grouping) / grouped if grouped else None,
            "flattened": sum(x.flattened for x in grouping),
            "wrongly_nested": sum(x.wrongly_nested for x in grouping),
            "wrong_group": sum(x.wrong_group for x in grouping),
        },
    }


def _validity_summary(results: list[SampleResult]) -> dict[str, object]:
    validities = [r.prediction.validity for r in results if r.prediction.validity]
    analyses = [r.prediction.analysis for r in results if r.prediction.analysis]
    return {
        "scored": len(validities),
        "status": dict(Counter(v.status for v in validities).most_common()),
        "mean_attempts": statistics.fmean(v.attempts for v in validities) if validities else None,
        "samples_with_repairs": sum(v.repairs > 0 for v in validities),
        "truncated_outputs": sum(
            any(a.output.finish_reason == "length" for a in x.extraction.attempts) for x in analyses
        ),
    }


def _qa_summary(results: list[SampleResult]) -> dict[str, object]:
    outcomes = [o for r in results for o in r.qa]
    by_kind: dict[str, dict[str, float | int]] = {}
    for kind in QUESTION_KINDS:
        chosen = [o for o in outcomes if o.kind == kind]
        if chosen:
            by_kind[kind] = {
                "questions": len(chosen),
                "accuracy": sum(o.correct for o in chosen) / len(chosen),
            }
    return {
        "questions": len(outcomes),
        "accuracy": sum(o.correct for o in outcomes) / len(outcomes) if outcomes else None,
        "by_kind": by_kind,
    }


def _taxonomy(with_graph: list[SampleResult]) -> dict[str, object]:
    counts = [r.scores.errors for r in with_graph if r.scores.errors]
    table = {}
    for name in ErrorCounts.model_fields:
        values = [getattr(c, name) for c in counts]
        table[name] = {
            "total": sum(values),
            "per_sample": statistics.fmean(values) if values else None,
            "samples_affected": sum(v > 0 for v in values),
        }
    return {"samples": len(counts), "types": table}


def _latency(results: list[SampleResult]) -> dict[str, float | None]:
    values = sorted(r.prediction.latency_ms for r in results)
    if not values:
        return {"mean": None, "median": None, "p90": None, "p95": None, "max": None}

    def percentile(q: float) -> float:
        return values[min(len(values) - 1, round(q * (len(values) - 1)))]

    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "max": values[-1],
    }


def _breakdowns(results: list[SampleResult]) -> dict[str, dict[str, object]]:
    present = {k for r in results for k in r.attributes}
    keys = [k for k in BREAKDOWNS if k in present] + sorted(present - set(BREAKDOWNS))
    out: dict[str, dict[str, object]] = {}
    for key in keys:
        groups: dict[str | int, list[SampleResult]] = defaultdict(list)
        for r in results:
            if key in r.attributes:
                groups[r.attributes[key]].append(r)
        out[key] = {
            str(value): {
                "samples": len(members),
                **{m: macro(members, m)["mean"] for m in BREAKDOWN_METRICS},
            }
            for value, members in sorted(groups.items(), key=lambda kv: (str(type(kv[0])), kv[0]))
        }
    return out
