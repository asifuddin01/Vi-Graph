"use client";

import { useState } from "react";

import GraphEditor from "@/components/editor/GraphEditor";
import MermaidView from "@/components/MermaidView";
import type { AnalyzeResponse, Change, EditedGraph, ExtractionStatus } from "@/lib/api";

const STATUS: Record<ExtractionStatus, { text: string; tone: string }> = {
  valid_first_attempt: {
    text: "Valid",
    tone: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  },
  valid_after_retry: {
    text: "Valid after retry",
    tone: "bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300",
  },
  repaired: {
    text: "Repaired",
    tone: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  },
  failed: {
    text: "Failed",
    tone: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  },
};

export default function ResultPanel({ result }: { result: AnalyzeResponse }) {
  const { metrics } = result;
  const status = STATUS[result.status];
  const [edited, setEdited] = useState<EditedGraph | null>(result.edited);
  // Everything below the editor reflects the latest saved edit, if there is one.
  const graph = edited?.graph ?? result.graph;
  const mermaid = edited?.mermaid ?? result.mermaid;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <span
          data-testid="result-status"
          className={`rounded-full px-3 py-1 text-xs font-semibold ${status.tone}`}
        >
          {status.text}
        </span>
        {graph && <Chip>{graph.diagram_type.replaceAll("_", " ")}</Chip>}
        {metrics.cached && <Chip>cached</Chip>}
        {edited && <Chip>edited · v{edited.version}</Chip>}
        <span className="ml-auto text-xs text-zinc-500">
          {result.model.model_id} · {Math.round(metrics.latency_ms)} ms
        </span>
      </div>

      <dl className="grid grid-cols-4 gap-2 text-center">
        <Metric label="Nodes" value={metrics.nodes ?? "–"} />
        <Metric label="Edges" value={metrics.edges ?? "–"} />
        <Metric label="Attempts" value={metrics.attempts} />
        <Metric label="Repairs" value={metrics.repairs} />
      </dl>

      {result.failure_reason && (
        <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {result.failure_reason}
        </p>
      )}

      <GraphEditor
        diagramId={result.diagram_id}
        original={result.graph}
        edited={result.edited}
        onSaved={setEdited}
      />

      {mermaid && <MermaidView source={mermaid} />}

      <div className="flex flex-col gap-2">
        {graph && (
          <Collapsible title={`Nodes (${graph.nodes.length}) & edges (${graph.edges.length})`}>
            <div className="flex flex-col gap-3">
              <Table
                head={["id", "label", "type", "group"]}
                rows={graph.nodes.map((n) => [n.id, n.label, n.type, n.group_id ?? ""])}
              />
              <Table
                head={["from", "to", "relation", "label"]}
                rows={graph.edges.map((e) => [e.source, e.target, e.relation, e.label ?? ""])}
              />
            </div>
          </Collapsible>
        )}
        {result.repairs.length > 0 && (
          <ChangeList title={`Repairs (${result.repairs.length})`} changes={result.repairs} />
        )}
        {result.normalization_changes.length > 0 && (
          <ChangeList
            title={`Normalization (${result.normalization_changes.length})`}
            changes={result.normalization_changes}
          />
        )}
        {result.attempts.map((attempt) => (
          <Collapsible
            key={attempt.number}
            title={`Attempt ${attempt.number} · ${attempt.valid ? "valid" : "invalid"}${
              attempt.finish_reason === "length" ? " · truncated" : ""
            }`}
          >
            {attempt.problems.length > 0 && (
              <ul className="mb-2 list-disc pl-5 text-xs text-red-700 dark:text-red-400">
                {attempt.problems.map((problem) => (
                  <li key={problem}>{problem}</li>
                ))}
              </ul>
            )}
            <Code>{attempt.raw_output || "(empty response)"}</Code>
          </Collapsible>
        ))}
        {graph && (
          <Collapsible title="Graph JSON">
            <Code>{JSON.stringify(graph, null, 2)}</Code>
          </Collapsible>
        )}
      </div>
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
      {children}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md bg-zinc-50 py-2 dark:bg-zinc-900">
      <dt className="text-[11px] uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

function Table({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-left text-xs">
        <thead className="bg-zinc-50 text-zinc-500 dark:bg-zinc-900">
          <tr>
            {head.map((h) => (
              <th key={h} className="px-2 py-1.5 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-zinc-100 dark:border-zinc-800">
              {row.map((cell, j) => (
                <td key={j} className="px-2 py-1.5 font-mono">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChangeList({ title, changes }: { title: string; changes: Change[] }) {
  return (
    <Collapsible title={title}>
      <ul className="flex flex-col gap-1 text-xs">
        {changes.map((change, i) => (
          <li key={i}>
            <code className="text-zinc-500">{change.code}</code> {change.message}
          </li>
        ))}
      </ul>
    </Collapsible>
  );
}

function Collapsible({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <details className="rounded-md border border-zinc-200 px-3 py-2 dark:border-zinc-800">
      <summary className="cursor-pointer text-sm font-medium">{title}</summary>
      <div className="mt-2">{children}</div>
    </details>
  );
}

function Code({ children }: { children: string }) {
  return (
    <pre className="max-h-80 overflow-auto rounded bg-zinc-50 p-2 text-[11px] leading-relaxed dark:bg-zinc-900">
      {children}
    </pre>
  );
}
