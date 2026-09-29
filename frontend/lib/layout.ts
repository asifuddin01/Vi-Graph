// Automatic layout for the graph editor with ELK's layered algorithm (top-down).
// Groups are laid out as real nested ELK nodes, so members sit inside their container;
// positions come back relative to the parent, which is React Flow's convention too.

import ELK, { type ElkExtendedEdge, type ElkNode } from "elkjs/lib/elk.bundled.js";

import type { DiagramFlowEdge, DiagramFlowNode } from "@/lib/graph";

const elk = new ELK();

export const NODE_HEIGHT = 44;
const EMPTY_GROUP = { width: 200, height: 90 };
const GROUP_HEADER = 32;

export type Layout = Record<string, [number, number]>;

/** Width of a node box; labels wrap beyond the maximum. */
export function nodeWidth(label: string): number {
  return Math.min(260, Math.max(112, 7.5 * label.length + 40));
}

export async function layoutNodes(
  nodes: DiagramFlowNode[],
  edges: DiagramFlowEdge[],
): Promise<DiagramFlowNode[]> {
  try {
    return await elkLayout(nodes, edges);
  } catch {
    // ELK rejects a few unusual hierarchies (e.g. a group wired to its own member).
    return gridLayout(nodes);
  }
}

/** Positions saved with an edited graph (§11), for the nodes they cover. */
export function applyLayout(nodes: DiagramFlowNode[], layout: Layout): DiagramFlowNode[] {
  return nodes.map((node) =>
    layout[node.id] ? { ...node, position: { x: layout[node.id][0], y: layout[node.id][1] } } : node,
  );
}

export function currentLayout(nodes: DiagramFlowNode[]): Layout {
  return Object.fromEntries(
    nodes.map((node) => [node.id, [Math.round(node.position.x), Math.round(node.position.y)]]),
  );
}

async function elkLayout(
  nodes: DiagramFlowNode[],
  edges: DiagramFlowEdge[],
): Promise<DiagramFlowNode[]> {
  const children = new Map<string | undefined, DiagramFlowNode[]>();
  for (const node of nodes) {
    const siblings = children.get(node.parentId) ?? [];
    siblings.push(node);
    children.set(node.parentId, siblings);
  }

  const toElk = (node: DiagramFlowNode): ElkNode => {
    const members = children.get(node.id) ?? [];
    if (node.type === "group" && members.length) {
      return {
        id: node.id,
        layoutOptions: { "elk.padding": `[top=${GROUP_HEADER + 12},left=16,bottom=16,right=16]` },
        children: members.map(toElk),
      };
    }
    if (node.type === "group") return { id: node.id, ...EMPTY_GROUP };
    return { id: node.id, width: nodeWidth(node.data.label), height: NODE_HEIGHT };
  };

  const root: ElkNode = {
    id: "__root__",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "DOWN",
      "elk.hierarchyHandling": "INCLUDE_CHILDREN",
      "elk.layered.spacing.nodeNodeBetweenLayers": "56",
      "elk.spacing.nodeNode": "40",
      "elk.padding": "[top=24,left=24,bottom=24,right=24]",
    },
    children: (children.get(undefined) ?? []).map(toElk),
    edges: edges.map(
      (edge): ElkExtendedEdge => ({ id: edge.id, sources: [edge.source], targets: [edge.target] }),
    ),
  };

  const placed = new Map<string, ElkNode>();
  const collect = (node: ElkNode) => {
    placed.set(node.id, node);
    node.children?.forEach(collect);
  };
  collect(await elk.layout(root));

  return nodes.map((node) => {
    const box = placed.get(node.id);
    const position = { x: box?.x ?? 0, y: box?.y ?? 0 };
    if (node.type === "group") {
      const size = { width: box?.width ?? EMPTY_GROUP.width, height: box?.height ?? EMPTY_GROUP.height };
      return { ...node, position, style: { ...node.style, ...size } };
    }
    return { ...node, position, style: { ...node.style, width: nodeWidth(node.data.label) } };
  });
}

function gridLayout(nodes: DiagramFlowNode[]): DiagramFlowNode[] {
  const perRow = new Map<string | undefined, number>();
  return nodes.map((node) => {
    const index = perRow.get(node.parentId) ?? 0;
    perRow.set(node.parentId, index + 1);
    const inGroup = node.parentId !== undefined;
    const position = {
      x: (inGroup ? 16 : 24) + (index % 3) * 280,
      y: (inGroup ? GROUP_HEADER + 12 : 24) + Math.floor(index / 3) * 100,
    };
    if (node.type === "group") {
      return { ...node, position, style: { ...node.style, width: 860, height: 420 } };
    }
    return { ...node, position, style: { ...node.style, width: nodeWidth(node.data.label) } };
  });
}
