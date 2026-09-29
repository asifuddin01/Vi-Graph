"""Render a run summary as a markdown report (numbers only as measured, §39)."""

from __future__ import annotations

from evaluation.results import RunInfo

HEADLINE = [
    ("Node F1", "node_f1"),
    ("Edge F1", "edge_f1"),
    ("Edge F1 (strict)", "edge_strict_f1"),
    ("Graph similarity", "graph_similarity"),
    ("Label accuracy", "label_accuracy"),
    ("Structural QA", "qa_accuracy"),
    ("Diagram type", "diagram_type_accuracy"),
    ("Valid (first attempt)", "valid_first_attempt"),
    ("Valid (bare JSON)", "valid_bare_json"),
    ("Valid (post-repair)", "valid_post_repair"),
]
BREAKDOWN_COLUMNS = [
    ("Node F1", "node_f1"),
    ("Edge F1", "edge_f1"),
    ("Strict", "edge_strict_f1"),
    ("Graph sim.", "graph_similarity"),
    ("Labels", "label_accuracy"),
    ("QA", "qa_accuracy"),
    ("Valid", "valid_post_repair"),
]


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "–"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_report(run: RunInfo, summary: dict) -> str:
    macro = summary["macro"]
    pooled = summary["pooled"]
    lines = [
        f"# Evaluation run `{run.name}`",
        "",
        f"- Predictor: `{run.config.predictor}`"
        + (f" · model `{run.config.model_id}`" if run.config.model_id else "")
        + (f" · adapter `{run.config.adapter}`" if run.config.adapter else ""),
        f"- Data: `{run.split.dataset}` split `{run.split.split}` · "
        f"{summary['samples']} of {run.split.samples} samples · "
        f"split hash `{run.split.split_hash[:12]}`",
        f"- Graph produced for {summary['with_graph']} samples; predictor errors: "
        f"{summary['errors']}",
        "",
        "## Headline (mean over samples; failures count as 0)",
        "",
        "| Metric | Mean | Std | n |",
        "| --- | --- | --- | --- |",
    ]
    for label, key in HEADLINE:
        m = macro[key]
        lines.append(f"| {label} | {fmt(m['mean'])} | {fmt(m['std'])} | {m['n']} |")

    nodes, edges, strict = pooled["nodes"], pooled["edges"], pooled["edges_strict"]
    lines += [
        "",
        "## Pooled over all nodes / edges (micro)",
        "",
        "| | Precision | Recall | F1 | TP | FP | FN |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, p in (("Nodes", nodes), ("Edges", edges), ("Edges (strict)", strict)):
        lines.append(
            f"| {label} | {fmt(p['precision'])} | {fmt(p['recall'])} | {fmt(p['f1'])} "
            f"| {p['tp']} | {p['fp']} | {p['fn']} |"
        )

    labels, text, grouping = pooled["labels"], pooled["edge_text"], pooled["grouping"]
    lines += [
        "",
        "## Labels, edge text, grouping (matched items only)",
        "",
        f"- Labels ({labels['matched']} matched): exact {fmt(labels['exact'])}, "
        f"case-insensitive {fmt(labels['exact_casefold'])}, similarity "
        f"{fmt(labels['mean_similarity'])}, CER {fmt(labels['cer'])}, WER {fmt(labels['wer'])}",
        f"- Edge text ({text['matched_with_text']} labeled edges matched): accuracy "
        f"{fmt(text['accuracy'])}; lost {text['lost']}, wrong {text['wrong']}, "
        f"hallucinated {text['hallucinated']}",
        f"- Grouping ({grouping['matched']} matched nodes): accuracy "
        f"{fmt(grouping['accuracy'])}; flattened {grouping['flattened']}, wrongly nested "
        f"{grouping['wrongly_nested']}, wrong group {grouping['wrong_group']}",
    ]

    validity = summary["validity"]
    if validity["scored"]:
        lines += [
            "",
            "## Output validity (§20.2)",
            "",
            "- Status: "
            + ", ".join(f"{k} {v}" for k, v in validity["status"].items())
            + f" · mean attempts {fmt(validity['mean_attempts'], 2)} · "
            f"with repairs {validity['samples_with_repairs']} · "
            f"truncated outputs {validity['truncated_outputs']}",
            f"- Attempt 1 as-is, no retry/repair/normalization (§24D): node F1 "
            f"{fmt(macro['first_attempt_node_f1']['mean'])}, edge F1 "
            f"{fmt(macro['first_attempt_edge_f1']['mean'])}, graph similarity "
            f"{fmt(macro['first_attempt_graph_similarity']['mean'])}",
        ]

    qa = summary["qa"]
    lines += [
        "",
        f"## Structural QA (§20.7): {fmt(qa['accuracy'])} over {qa['questions']} questions",
        "",
        "| Kind | Questions | Accuracy |",
        "| --- | --- | --- |",
    ]
    for kind, row in qa["by_kind"].items():
        lines.append(f"| {kind} | {row['questions']} | {fmt(row['accuracy'])} |")

    for key, table in summary["breakdowns"].items():
        lines += [
            "",
            f"## By {key.replace('_', ' ')}",
            "",
            "| Value | n | " + " | ".join(label for label, _ in BREAKDOWN_COLUMNS) + " |",
            "| --- | --- | " + " | ".join("---" for _ in BREAKDOWN_COLUMNS) + " |",
        ]
        for value, row in table.items():
            cells = " | ".join(fmt(row[m]) for _, m in BREAKDOWN_COLUMNS)
            lines.append(f"| {value} | {row['samples']} | {cells} |")

    taxonomy = summary["errors_taxonomy"]
    lines += [
        "",
        f"## Error taxonomy (§23; {taxonomy['samples']} samples with a graph)",
        "",
        "| Type | Total | Per sample | Samples affected |",
        "| --- | --- | --- | --- |",
    ]
    for name, row in taxonomy["types"].items():
        lines.append(
            f"| {name.replace('_', ' ')} | {row['total']} | {fmt(row['per_sample'], 2)} "
            f"| {row['samples_affected']} |"
        )

    latency = summary["latency_ms"]
    lines += [
        "",
        "## Latency per sample (ms, whole pipeline incl. retries)",
        "",
        f"mean {fmt(latency['mean'], 0)} · median {fmt(latency['median'], 0)} · "
        f"p90 {fmt(latency['p90'], 0)} · p95 {fmt(latency['p95'], 0)} · "
        f"max {fmt(latency['max'], 0)}",
        "",
        "## Reproducibility (§18.1)",
        "",
    ]
    meta = run.metadata
    if meta is not None:
        lines += [
            f"- Model: backend `{meta.model.backend}`, id `{meta.model.model_id}`, revision "
            f"`{meta.model.revision}`, adapter `{meta.model.adapter_path}`",
            f"- Prompts: `{meta.prompt_id}` ({meta.prompt_sha256[:12]}), "
            f"`{meta.correction_prompt_id}` ({meta.correction_prompt_sha256[:12]})",
            f"- Decoding: temperature {meta.params.temperature}, top_p {meta.params.top_p}, "
            f"max_new_tokens {meta.params.max_new_tokens}, seed {meta.params.seed}; "
            f"image max side {meta.image_max_side}",
        ]
    if run.adapter_config:
        lines.append(
            "- Adapter: "
            + ", ".join(f"{k} {v}" for k, v in run.adapter_config.items() if v is not None)
        )
    versions = ", ".join(
        f"{k} {v}" for k, v in run.versions.items() if not isinstance(v, dict) and v is not None
    )
    lines += [
        f"- Versions: {versions}",
        f"- Split `{run.split.split}` hash `{run.split.split_hash}`; ground truth "
        f"`{run.split.graph_hash}`",
        f"- Started {run.created_at:%Y-%m-%d %H:%M} UTC"
        + (f", completed {run.completed_at:%Y-%m-%d %H:%M} UTC" if run.completed_at else ""),
        "",
    ]
    return "\n".join(lines)
