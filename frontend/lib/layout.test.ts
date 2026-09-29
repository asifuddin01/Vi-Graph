import { describe, expect, it } from "vitest";

import type { DiagramGraph } from "@/lib/api";
import { toFlow } from "@/lib/graph";
import { applyLayout, currentLayout, layoutNodes, NODE_HEIGHT, nodeWidth } from "@/lib/layout";

const edge = (source: string, target: string) => ({
  source,
  target,
  relation: "flows_to",
  label: null,
  condition: null,
});

const SPEC: DiagramGraph = {
  schema_version: "2.0",
  diagram_type: "neural_network",
  nodes: [
    { id: "n1", label: "Input Image", type: "input", group_id: null },
    { id: "n2", label: "CNN Encoder", type: "module", group_id: null },
    { id: "n3", label: "Transformer Encoder", type: "module", group_id: null },
    { id: "n4", label: "Feature Fusion", type: "fusion", group_id: null },
    { id: "n5", label: "Classifier", type: "output", group_id: null },
  ],
  edges: [edge("n1", "n2"), edge("n1", "n3"), edge("n2", "n4"), edge("n3", "n4"), edge("n4", "n5")],
};

describe("layoutNodes", () => {
  it("lays the flow out top-down with parallel branches side by side", async () => {
    const { nodes, edges } = toFlow(SPEC);

    const laid = Object.fromEntries((await layoutNodes(nodes, edges)).map((n) => [n.id, n]));

    expect(laid.n1.position.y).toBeLessThan(laid.n2.position.y);
    expect(laid.n2.position.y).toBe(laid.n3.position.y);
    expect(laid.n2.position.x).not.toBe(laid.n3.position.x);
    expect(laid.n4.position.y).toBeLessThan(laid.n5.position.y);
    expect(laid.n2.style?.width).toBe(nodeWidth("CNN Encoder"));
  });

  it("places group members inside their group, relative to it", async () => {
    const graph: DiagramGraph = {
      ...SPEC,
      nodes: [
        { id: "g", label: "Encoder Block", type: "group", group_id: null },
        { id: "a", label: "Conv", type: "module", group_id: "g" },
        { id: "b", label: "ReLU", type: "operation", group_id: "g" },
        { id: "out", label: "Out", type: "output", group_id: null },
      ],
      edges: [edge("a", "b"), edge("b", "out")],
    };
    const { nodes, edges } = toFlow(graph);

    const laid = Object.fromEntries((await layoutNodes(nodes, edges)).map((n) => [n.id, n]));

    const width = Number(laid.g.style?.width);
    const height = Number(laid.g.style?.height);
    for (const id of ["a", "b"]) {
      const { x, y } = laid[id].position;
      expect(x).toBeGreaterThanOrEqual(0);
      expect(y).toBeGreaterThan(0); // below the group's header
      expect(x + nodeWidth(laid[id].data.label)).toBeLessThanOrEqual(width);
      expect(y + NODE_HEIGHT).toBeLessThanOrEqual(height);
    }
  });

  it("gives an empty group a default size", async () => {
    const { nodes, edges } = toFlow({
      ...SPEC,
      nodes: [{ id: "g", label: "Empty", type: "group", group_id: null }],
      edges: [],
    });

    const [group] = await layoutNodes(nodes, edges);

    expect(group.style).toMatchObject({ width: 200, height: 90 });
  });
});

describe("saved layouts", () => {
  it("round-trips positions and ignores unknown ids", () => {
    const { nodes } = toFlow(SPEC);

    const placed = applyLayout(nodes, { n1: [10, 20], ghost: [1, 1] });

    expect(placed[0].position).toEqual({ x: 10, y: 20 });
    expect(placed[1].position).toEqual({ x: 0, y: 0 });
    expect(currentLayout(placed).n1).toEqual([10, 20]);
  });
});
