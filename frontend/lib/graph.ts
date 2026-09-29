// Conversion between the canonical graph (schema v2, spec §7) and React Flow's model.
// Pure functions — no React — so they can be unit-tested.

import { MarkerType, type Edge, type Node } from "@xyflow/react";

import type { DiagramGraph, GraphEdge, GraphNode } from "@/lib/api";

export const SCHEMA_VERSION = "2.0";

// Mirrors backend/app/schemas/graph.py.
export const DIAGRAM_TYPES = [
  "neural_network",
  "ml_pipeline",
  "flowchart",
  "system_architecture",
  "data_pipeline",
  "scientific_workflow",
  "uml",
  "other",
] as const;

export const NODE_TYPES = [
  "input",
  "module",
  "operation",
  "decision",
  "fusion",
  "output",
  "group",
  "unknown",
] as const;

export const RELATIONS = [
  "flows_to",
  "contains",
  "branches_to",
  "merges_to",
  "inherits_from",
  "composes",
  "aggregates",
  "depends_on",
  "unknown",
] as const;

const PLAIN_RELATIONS = new Set(["flows_to", "branches_to", "merges_to", "unknown"]);

export type DiagramNodeData = {
  label: string;
  nodeType: string;
  bbox?: [number, number, number, number];
  confidence?: number;
};

// "diagram" for ordinary nodes; "group" for containers (their members set parentId).
export type DiagramFlowNode = Node<DiagramNodeData, "diagram" | "group">;

export type DiagramEdgeData = {
  relation: string;
  label: string | null;
  condition: string | null;
};

export type DiagramFlowEdge = Edge<DiagramEdgeData>;

export function toFlow(graph: DiagramGraph): {
  nodes: DiagramFlowNode[];
  edges: DiagramFlowEdge[];
} {
  return {
    nodes: parentsFirst(graph.nodes).map(toFlowNode),
    edges: graph.edges.map((edge, index) =>
      toFlowEdge(`e${index}`, edge.source, edge.target, {
        relation: edge.relation,
        label: edge.label,
        condition: edge.condition,
      }),
    ),
  };
}

export function toFlowNode(node: GraphNode): DiagramFlowNode {
  const data: DiagramNodeData = { label: node.label, nodeType: node.type };
  if (node.bbox) data.bbox = node.bbox;
  if (node.confidence !== undefined) data.confidence = node.confidence;
  return {
    id: node.id,
    type: node.type === "group" ? "group" : "diagram",
    position: { x: 0, y: 0 },
    data,
    ...(node.group_id ? { parentId: node.group_id, expandParent: true } : {}),
  };
}

export function toFlowEdge(
  id: string,
  source: string,
  target: string,
  data: DiagramEdgeData,
): DiagramFlowEdge {
  return { id, source, target, data, ...edgeAppearance(data) };
}

/** Visible label and styling for an edge; mirrors the Mermaid export. */
export function edgeAppearance(data: DiagramEdgeData): Partial<DiagramFlowEdge> {
  let text = data.label ?? data.condition ?? "";
  if (!PLAIN_RELATIONS.has(data.relation)) {
    const relation = data.relation.replaceAll("_", " ");
    text = text ? `${text} (${relation})` : relation;
  }
  return {
    label: text || undefined,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: data.relation === "depends_on" ? { strokeDasharray: "6 4" } : undefined,
  };
}

export function fromFlow(
  nodes: DiagramFlowNode[],
  edges: DiagramFlowEdge[],
  diagramType: string,
): DiagramGraph {
  return {
    schema_version: SCHEMA_VERSION,
    diagram_type: diagramType,
    nodes: nodes.map((node) => {
      const out: GraphNode = {
        id: node.id,
        label: node.data.label,
        type: node.data.nodeType,
        group_id: node.parentId ?? null,
      };
      if (node.data.bbox) out.bbox = node.data.bbox;
      if (node.data.confidence !== undefined) out.confidence = node.data.confidence;
      return out;
    }),
    edges: edges.map(
      (edge): GraphEdge => ({
        source: edge.source,
        target: edge.target,
        relation: edge.data?.relation ?? "flows_to",
        label: edge.data?.label ?? null,
        condition: edge.data?.condition ?? null,
      }),
    ),
  };
}

/** React Flow needs every parent before its children; otherwise keep the given order. */
export function parentsFirst<T extends { id: string; group_id: string | null }>(nodes: T[]): T[] {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const out: T[] = [];
  const placed = new Set<string>();
  const visiting = new Set<string>();
  const place = (node: T) => {
    if (placed.has(node.id) || visiting.has(node.id)) return;
    visiting.add(node.id);
    const parent = node.group_id ? byId.get(node.group_id) : undefined;
    if (parent) place(parent);
    visiting.delete(node.id);
    placed.add(node.id);
    out.push(node);
  };
  nodes.forEach(place);
  return out;
}

/** The next free id of the form n<k>. */
export function nextNodeId(existing: Iterable<string>): string {
  let max = 0;
  for (const id of existing) {
    const match = /^n(\d+)$/.exec(id);
    if (match) max = Math.max(max, Number(match[1]));
  }
  return `n${max + 1}`;
}
