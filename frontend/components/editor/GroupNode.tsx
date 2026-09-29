"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";

import type { DiagramFlowNode } from "@/lib/graph";

/** A container (type "group", spec §7.1); members are React Flow children of it. */
export default function GroupNode({ id, data, selected }: NodeProps<DiagramFlowNode>) {
  return (
    <div
      data-testid={`node-${id}`}
      className={`h-full w-full rounded-lg border-2 border-dashed bg-zinc-100/50 dark:bg-zinc-800/30 ${
        selected ? "border-sky-500" : "border-zinc-400 dark:border-zinc-600"
      }`}
    >
      <Handle type="target" position={Position.Top} />
      <div className="px-2.5 py-1.5 text-xs font-semibold text-zinc-600 dark:text-zinc-300">
        {data.label}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
