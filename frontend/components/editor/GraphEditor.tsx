"use client";

import "@xyflow/react/dist/style.css";

import {
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type EdgeChange,
  type NodeChange,
  type OnSelectionChangeParams,
} from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import DiagramNode from "@/components/editor/DiagramNode";
import GroupNode from "@/components/editor/GroupNode";
import Inspector from "@/components/editor/Inspector";
import {
  ApiError,
  downloadBlob,
  EXPORT_EXTENSIONS,
  exportGraph,
  saveGraph,
  type DiagramGraph,
  type EditedGraph,
  type ExportFormat,
  type Grounding,
} from "@/lib/api";
import {
  DIAGRAM_TYPES,
  edgeAppearance,
  fromFlow,
  nextNodeId,
  parentsFirst,
  toFlow,
  toFlowEdge,
  type DiagramEdgeData,
  type DiagramFlowEdge,
  type DiagramFlowNode,
  type DiagramNodeData,
} from "@/lib/graph";
import { applyLayout, currentLayout, layoutNodes, nodeWidth, type Layout } from "@/lib/layout";

const nodeTypes = { diagram: DiagramNode, group: GroupNode };
const EMPTY_GROUP_STYLE = { width: 200, height: 90 };

type Props = {
  diagramId: string;
  /** The model's reconstruction; null when extraction failed (start from scratch). */
  original: DiagramGraph | null;
  /** The latest saved edit, if any; the editor opens on it. */
  edited: EditedGraph | null;
  onSaved: (edited: EditedGraph) => void;
  /** Nodes/edges to highlight, e.g. the grounding of a QA answer (§12). */
  highlight?: Grounding | null;
};

type SaveState =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; version: number }
  | { kind: "error"; message: string; problems: string[] }
  | { kind: "notice"; message: string };

export default function GraphEditor(props: Props) {
  return (
    <ReactFlowProvider>
      <Editor {...props} />
    </ReactFlowProvider>
  );
}

function Editor({ diagramId, original, edited, onSaved, highlight }: Props) {
  // Captured once: later prop changes must not wipe out the user's edits.
  const [start] = useState(() => ({
    graph: edited?.graph ?? original,
    layout: edited?.layout ?? null,
  }));
  const [diagramType, setDiagramType] = useState(start.graph?.diagram_type ?? "other");
  const [nodes, setNodes, onNodesChange] = useNodesState<DiagramFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<DiagramFlowEdge>([]);
  const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
  const [selectedEdge, setSelectedEdge] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [save, setSave] = useState<SaveState>({ kind: "idle" });
  // The latest saved version: from props at first, then from this editor's own saves.
  const [savedVersion, setSavedVersion] = useState<number | null>(edited?.version ?? null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const { fitView, screenToFlowPosition } = useReactFlow();

  const fit = useCallback(() => {
    window.requestAnimationFrame(() => void fitView({ padding: 0.15 }));
  }, [fitView]);

  const show = useCallback(
    async (graph: DiagramGraph | null, layout: Layout | null) => {
      const flow = graph ? toFlow(graph) : { nodes: [], edges: [] };
      let laid = await layoutNodes(flow.nodes, flow.edges);
      if (layout) laid = applyLayout(laid, layout);
      setNodes(laid);
      setEdges(flow.edges);
      fit();
    },
    [setNodes, setEdges, fit],
  );

  useEffect(() => {
    void show(start.graph, start.layout);
  }, [show, start]);

  const relayout = useCallback(
    async (next: DiagramFlowNode[], nextEdges: DiagramFlowEdge[]) => {
      setNodes(await layoutNodes(orderParentsFirst(next), nextEdges));
      fit();
    },
    [setNodes, fit],
  );

  const handleNodesChange = useCallback(
    (changes: NodeChange<DiagramFlowNode>[]) => {
      onNodesChange(changes);
      if (changes.some((c) => c.type !== "select" && c.type !== "dimensions")) setDirty(true);
    },
    [onNodesChange],
  );

  const handleEdgesChange = useCallback(
    (changes: EdgeChange<DiagramFlowEdge>[]) => {
      onEdgesChange(changes);
      if (changes.some((c) => c.type !== "select")) setDirty(true);
    },
    [onEdgesChange],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      const data: DiagramEdgeData = { relation: "flows_to", label: null, condition: null };
      setEdges((current) =>
        addEdge(toFlowEdge(newEdgeId(), connection.source, connection.target, data), current),
      );
      setDirty(true);
    },
    [setEdges],
  );

  const onSelectionChange = useCallback(
    ({ nodes: picked, edges: pickedEdges }: OnSelectionChangeParams) => {
      setSelectedNodes(picked.map((n) => n.id));
      setSelectedEdge(picked.length === 0 && pickedEdges.length === 1 ? pickedEdges[0].id : null);
    },
    [],
  );

  const updateNode = useCallback(
    (id: string, patch: Partial<DiagramNodeData>) => {
      setNodes((current) =>
        current.map((node) => {
          if (node.id !== id) return node;
          const data = { ...node.data, ...patch };
          return data.nodeType === "group"
            ? { ...node, data, type: "group", style: { ...EMPTY_GROUP_STYLE, ...node.style } }
            : { ...node, data, type: "diagram", style: { width: nodeWidth(data.label) } };
        }),
      );
      setDirty(true);
    },
    [setNodes],
  );

  const updateEdge = useCallback(
    (id: string, patch: Partial<DiagramEdgeData>) => {
      setEdges((current) =>
        current.map((edge) => {
          if (edge.id !== id || !edge.data) return edge;
          const data = { ...edge.data, ...patch };
          return { ...edge, data, ...edgeAppearance(data) };
        }),
      );
      setDirty(true);
    },
    [setEdges],
  );

  const setParent = useCallback(
    (id: string, parentId: string | null) => {
      const next = nodes.map((node) => (node.id === id ? withParent(node, parentId) : node));
      setDirty(true);
      void relayout(next, edges);
    },
    [nodes, edges, relayout],
  );

  function addNode() {
    const id = nextNodeId(nodes.map((n) => n.id));
    const rect = canvasRef.current?.getBoundingClientRect();
    const center = rect
      ? screenToFlowPosition({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
      : { x: 0, y: 0 };
    const label = "New node";
    const node: DiagramFlowNode = {
      id,
      type: "diagram",
      position: { x: center.x - nodeWidth(label) / 2, y: center.y - 22 },
      data: { label, nodeType: "module" },
      style: { width: nodeWidth(label) },
      selected: true,
    };
    setNodes((current) => [...current.map((n) => ({ ...n, selected: false })), node]);
    setDirty(true);
  }

  function groupSelected() {
    const chosen = nodes.filter((n) => selectedNodes.includes(n.id));
    if (!chosen.length) return;
    const parents = new Set(chosen.map((n) => n.parentId ?? null));
    if (parents.size > 1) {
      setSave({ kind: "notice", message: "Select nodes that share the same group to group them." });
      return;
    }
    const parentId = chosen[0].parentId ?? null;
    const id = nextNodeId(nodes.map((n) => n.id));
    const group = withParent(
      { id, type: "group", position: { x: 0, y: 0 }, data: { label: "Group", nodeType: "group" } },
      parentId,
    );
    const next = [
      ...nodes.map((n) => (selectedNodes.includes(n.id) ? { ...withParent(n, id), selected: false } : n)),
      { ...group, selected: true },
    ];
    setDirty(true);
    void relayout(next, edges);
  }

  function ungroup() {
    const group = nodes.find((n) => n.id === selectedNodes[0] && n.type === "group");
    if (!group) return;
    const next = nodes
      .filter((n) => n.id !== group.id)
      .map((n) => (n.parentId === group.id ? withParent(n, group.parentId ?? null) : n));
    const nextEdges = edges.filter((e) => e.source !== group.id && e.target !== group.id);
    setEdges(nextEdges);
    setDirty(true);
    void relayout(next, nextEdges);
  }

  function reset() {
    void show(original, null);
    setDiagramType(original?.diagram_type ?? "other");
    // With a saved edit, the AI version differs from what is saved: allow saving it.
    setDirty(savedVersion !== null);
    setSave({ kind: "idle" });
  }

  async function saveNow() {
    setSave({ kind: "saving" });
    try {
      const view = await saveGraph(
        diagramId,
        fromFlow(nodes, edges, diagramType),
        currentLayout(nodes),
      );
      setDirty(false);
      setSavedVersion(view.version);
      setSave({ kind: "saved", version: view.version });
      onSaved(view);
    } catch (err) {
      setSave({
        kind: "error",
        message: err instanceof Error ? err.message : "Saving failed.",
        problems: err instanceof ApiError ? err.problems : [],
      });
    }
  }

  async function exportAs(format: ExportFormat) {
    try {
      const blob = await exportGraph(fromFlow(nodes, edges, diagramType), format);
      downloadBlob(blob, `vigraph-${diagramId.slice(0, 8)}.${EXPORT_EXTENSIONS[format]}`);
      setSave({ kind: "notice", message: `Exported ${format.toUpperCase()}.` });
    } catch (err) {
      setSave({
        kind: "error",
        message: err instanceof Error ? err.message : "Export failed.",
        problems: err instanceof ApiError ? err.problems : [],
      });
    }
  }

  // Highlighting only decorates what is rendered; it never touches the editor's state.
  const shownNodes = useMemo(() => {
    const lit = new Set(highlight?.nodes ?? []);
    return lit.size ? nodes.map((n) => (lit.has(n.id) ? { ...n, className: "vg-highlight" } : n)) : nodes;
  }, [nodes, highlight]);
  const shownEdges = useMemo(() => {
    const lit = new Set((highlight?.edges ?? []).map(([s, t]) => `${s}\u0000${t}`));
    return lit.size
      ? edges.map((e) =>
          lit.has(`${e.source}\u0000${e.target}`) ? { ...e, className: "vg-highlight", animated: true } : e,
        )
      : edges;
  }, [edges, highlight]);

  const singleNode = selectedNodes.length === 1 ? nodes.find((n) => n.id === selectedNodes[0]) : undefined;
  const edge = selectedEdge ? edges.find((e) => e.id === selectedEdge) : undefined;

  return (
    <div className="flex flex-col overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-800">
      <div className="flex flex-wrap items-center gap-1.5 border-b border-zinc-200 px-2 py-1.5 dark:border-zinc-800">
        <ToolButton onClick={addNode}>Add node</ToolButton>
        <ToolButton onClick={groupSelected} disabled={selectedNodes.length === 0}>
          Group
        </ToolButton>
        <ToolButton onClick={ungroup} disabled={singleNode?.type !== "group"}>
          Ungroup
        </ToolButton>
        <ToolButton onClick={() => void relayout(nodes, edges)} disabled={nodes.length === 0}>
          Re-layout
        </ToolButton>
        <ToolButton onClick={reset} disabled={original === null}>
          Reset to AI
        </ToolButton>
        <select
          aria-label="Diagram type"
          value={diagramType}
          onChange={(e) => {
            setDiagramType(e.target.value);
            setDirty(true);
          }}
          className="rounded border border-zinc-300 bg-white px-1.5 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-900"
        >
          {DIAGRAM_TYPES.map((type) => (
            <option key={type} value={type}>
              {type.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <select
          aria-label="Export"
          value=""
          disabled={nodes.length === 0}
          onChange={(e) => {
            if (e.target.value) void exportAs(e.target.value as ExportFormat);
          }}
          className="ml-auto rounded border border-zinc-300 bg-white px-1.5 py-1 text-xs disabled:opacity-40 dark:border-zinc-700 dark:bg-zinc-900"
        >
          <option value="">Export…</option>
          <option value="svg">SVG</option>
          <option value="png">PNG</option>
          <option value="pdf">PDF</option>
          <option value="json">JSON</option>
          <option value="mermaid">Mermaid</option>
        </select>
        <button
          type="button"
          onClick={() => void saveNow()}
          disabled={!dirty || nodes.length === 0 || save.kind === "saving"}
          className="rounded-md bg-zinc-900 px-3 py-1 text-xs font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          {save.kind === "saving" ? "Saving…" : "Save"}
        </button>
      </div>

      <div className="flex h-[520px]">
        <div ref={canvasRef} className="min-w-0 flex-1" data-testid="graph-editor">
          <ReactFlow
            nodes={shownNodes}
            edges={shownEdges}
            nodeTypes={nodeTypes}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={onConnect}
            onSelectionChange={onSelectionChange}
            deleteKeyCode={["Backspace", "Delete"]}
            colorMode="system"
            minZoom={0.2}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap pannable zoomable />
          </ReactFlow>
        </div>
        <Inspector
          node={singleNode}
          edge={edge}
          nodes={nodes}
          edges={edges}
          onNodeChange={updateNode}
          onNodeParentChange={setParent}
          onEdgeChange={updateEdge}
        />
      </div>

      <div
        role="status"
        data-testid="editor-status"
        className="border-t border-zinc-200 px-3 py-1.5 text-xs text-zinc-500 dark:border-zinc-800"
      >
        {save.kind === "saved" && `Saved as version ${save.version}.`}
        {save.kind === "notice" && save.message}
        {save.kind === "error" && (
          <span className="text-red-700 dark:text-red-400">
            {save.problems.length ? "Not saved — fix these problems:" : save.message}
            {save.problems.length > 0 && (
              <ul className="mt-1 list-disc pl-5">
                {save.problems.map((problem) => (
                  <li key={problem}>{problem}</li>
                ))}
              </ul>
            )}
          </span>
        )}
        {(save.kind === "idle" || save.kind === "saving") &&
          (dirty
            ? "Unsaved changes."
            : savedVersion !== null
              ? `Showing saved version ${savedVersion}.`
              : "Showing the model's reconstruction.")}
      </div>
    </div>
  );
}

function ToolButton({
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { children: React.ReactNode }) {
  return (
    <button
      type="button"
      className="rounded-md border border-zinc-300 px-2.5 py-1 text-xs font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-800"
      {...props}
    >
      {children}
    </button>
  );
}

function withParent(node: DiagramFlowNode, parentId: string | null): DiagramFlowNode {
  const next = { ...node };
  delete next.parentId;
  delete next.expandParent;
  return parentId ? { ...next, parentId, expandParent: true } : next;
}

function orderParentsFirst(nodes: DiagramFlowNode[]): DiagramFlowNode[] {
  return parentsFirst(nodes.map((node) => ({ id: node.id, group_id: node.parentId ?? null, node }))).map(
    (entry) => entry.node,
  );
}

function newEdgeId(): string {
  // Not crypto.randomUUID(): it only exists in secure contexts (HTTPS or localhost).
  return `e-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}
