"use client";

import {
  NODE_TYPES,
  RELATIONS,
  type DiagramEdgeData,
  type DiagramFlowEdge,
  type DiagramFlowNode,
  type DiagramNodeData,
} from "@/lib/graph";

type Props = {
  node?: DiagramFlowNode;
  edge?: DiagramFlowEdge;
  nodes: DiagramFlowNode[];
  edges: DiagramFlowEdge[];
  onNodeChange: (id: string, patch: Partial<DiagramNodeData>) => void;
  onNodeParentChange: (id: string, parentId: string | null) => void;
  onEdgeChange: (id: string, patch: Partial<DiagramEdgeData>) => void;
};

export default function Inspector(props: Props) {
  const { node, edge } = props;
  return (
    <aside
      aria-label="Inspector"
      className="flex w-60 shrink-0 flex-col gap-3 overflow-y-auto border-l border-zinc-200 p-3 text-xs dark:border-zinc-800"
    >
      {node ? (
        <NodeInspector {...props} node={node} />
      ) : edge ? (
        <EdgeInspector {...props} edge={edge} />
      ) : (
        <div className="flex flex-col gap-2 text-zinc-500">
          <p className="font-medium text-zinc-700 dark:text-zinc-300">Nothing selected</p>
          <p>Click a node or edge to edit it.</p>
          <p>Drag from a node&apos;s bottom handle to another node to add an edge.</p>
          <p>Select and press Delete to remove (deleting a group removes its contents).</p>
          <p>Ctrl/⌘-click, or Shift-drag a box, to select several nodes; then Group.</p>
        </div>
      )}
    </aside>
  );
}

function NodeInspector({
  node,
  nodes,
  edges,
  onNodeChange,
  onNodeParentChange,
}: Props & { node: DiagramFlowNode }) {
  const members = nodes.filter((n) => n.parentId === node.id);
  const blocked = descendants(node.id, nodes);
  const groups = nodes.filter((n) => n.type === "group" && n.id !== node.id && !blocked.has(n.id));
  const incoming = edges.filter((e) => e.target === node.id).length;
  const outgoing = edges.filter((e) => e.source === node.id).length;
  const blank = !node.data.label.trim();

  return (
    <>
      <p className="font-semibold text-zinc-700 dark:text-zinc-200">Node {node.id}</p>
      <Field label="Label">
        <input
          aria-label="Node label"
          value={node.data.label}
          onChange={(e) => onNodeChange(node.id, { label: e.target.value })}
          className={inputClass}
        />
        {blank && <span className="text-red-600">A label is required.</span>}
      </Field>
      <Field label="Type">
        <select
          aria-label="Node type"
          value={node.data.nodeType}
          onChange={(e) => onNodeChange(node.id, { nodeType: e.target.value })}
          className={inputClass}
        >
          {NODE_TYPES.map((type) => (
            <option key={type} value={type} disabled={members.length > 0 && type !== "group"}>
              {type}
            </option>
          ))}
        </select>
        {members.length > 0 && (
          <span className="text-zinc-500">Ungroup its {members.length} member(s) to change the type.</span>
        )}
      </Field>
      <Field label="Group">
        <select
          aria-label="Node group"
          value={node.parentId ?? ""}
          onChange={(e) => onNodeParentChange(node.id, e.target.value || null)}
          className={inputClass}
        >
          <option value="">(none)</option>
          {groups.map((group) => (
            <option key={group.id} value={group.id}>
              {group.data.label} ({group.id})
            </option>
          ))}
        </select>
      </Field>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-zinc-500">
        <dt>Incoming</dt>
        <dd>{incoming}</dd>
        <dt>Outgoing</dt>
        <dd>{outgoing}</dd>
        {node.data.bbox && (
          <>
            <dt>BBox</dt>
            <dd className="font-mono">{node.data.bbox.join(", ")}</dd>
          </>
        )}
        {node.data.confidence !== undefined && (
          <>
            <dt>Confidence</dt>
            <dd>{node.data.confidence.toFixed(2)}</dd>
          </>
        )}
      </dl>
    </>
  );
}

function EdgeInspector({ edge, nodes, onEdgeChange }: Props & { edge: DiagramFlowEdge }) {
  const label = (id: string) => nodes.find((n) => n.id === id)?.data.label ?? id;
  const data = edge.data ?? { relation: "flows_to", label: null, condition: null };
  return (
    <>
      <p className="font-semibold text-zinc-700 dark:text-zinc-200">
        {label(edge.source)} → {label(edge.target)}
      </p>
      <Field label="Relation">
        <select
          aria-label="Edge relation"
          value={data.relation}
          onChange={(e) => onEdgeChange(edge.id, { relation: e.target.value })}
          className={inputClass}
        >
          {RELATIONS.map((relation) => (
            <option key={relation} value={relation}>
              {relation}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Label">
        <input
          aria-label="Edge label"
          value={data.label ?? ""}
          placeholder="e.g. Yes / No"
          onChange={(e) => onEdgeChange(edge.id, { label: e.target.value || null })}
          className={inputClass}
        />
      </Field>
      <Field label="Condition">
        <input
          aria-label="Edge condition"
          value={data.condition ?? ""}
          placeholder="e.g. x > 0"
          onChange={(e) => onEdgeChange(edge.id, { condition: e.target.value || null })}
          className={inputClass}
        />
      </Field>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-medium text-zinc-600 dark:text-zinc-400">{label}</span>
      {children}
    </label>
  );
}

const inputClass =
  "rounded border border-zinc-300 bg-white px-2 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-900";

/** Ids of every node nested (at any depth) inside ``id``. */
function descendants(id: string, nodes: DiagramFlowNode[]): Set<string> {
  const found = new Set<string>();
  const stack = [id];
  while (stack.length) {
    const parent = stack.pop();
    for (const node of nodes) {
      if (node.parentId === parent && !found.has(node.id)) {
        found.add(node.id);
        stack.push(node.id);
      }
    }
  }
  return found;
}
