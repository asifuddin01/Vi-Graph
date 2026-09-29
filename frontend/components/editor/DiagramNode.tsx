"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";

import type { DiagramFlowNode } from "@/lib/graph";

// Shapes/colours by node type; they mirror the Mermaid export's shapes.
const SHAPE: Record<string, string> = {
  input: "rounded-full border-sky-500 bg-sky-50 dark:bg-sky-950/60",
  output: "rounded-full border-emerald-500 bg-emerald-50 dark:bg-emerald-950/60",
  module: "rounded-md border-zinc-400 bg-white dark:border-zinc-500 dark:bg-zinc-900",
  operation: "rounded-2xl border-indigo-400 bg-indigo-50 dark:bg-indigo-950/60",
  fusion: "rounded-md border-violet-500 bg-violet-50 dark:bg-violet-950/60",
  unknown: "rounded-md border-dashed border-zinc-400 bg-zinc-50 dark:bg-zinc-900",
};

export default function DiagramNode({ id, data, selected }: NodeProps<DiagramFlowNode>) {
  const ring = selected ? "ring-2 ring-sky-500 ring-offset-1 dark:ring-offset-zinc-950" : "";
  const decision = data.nodeType === "decision";
  return (
    <div
      data-testid={`node-${id}`}
      title={`${data.label} (${data.nodeType})`}
      className={`relative flex min-h-11 w-full items-center justify-center px-3 py-1.5 text-center text-xs text-zinc-900 dark:text-zinc-100 ${
        decision ? "" : `border-2 ${SHAPE[data.nodeType] ?? SHAPE.unknown}`
      } ${ring}`}
    >
      {decision && (
        // A diamond behind the label; the node's box stays rectangular for layout.
        <div className="absolute inset-0 bg-amber-300 [clip-path:polygon(50%_0,100%_50%,50%_100%,0_50%)] dark:bg-amber-700" />
      )}
      <Handle type="target" position={Position.Top} />
      <span className="relative leading-tight">{data.label}</span>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
