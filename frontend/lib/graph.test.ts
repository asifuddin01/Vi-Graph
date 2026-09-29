import { describe, expect, it } from "vitest";

import type { DiagramGraph } from "@/lib/api";
import { edgeAppearance, fromFlow, nextNodeId, parentsFirst, toFlow } from "@/lib/graph";

// The canonical example from spec §7.
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
  edges: [
    ["n1", "n2"],
    ["n1", "n3"],
    ["n2", "n4"],
    ["n3", "n4"],
    ["n4", "n5"],
  ].map(([source, target]) => ({
    source,
    target,
    relation: "flows_to",
    label: null,
    condition: null,
  })),
};

const NESTED: DiagramGraph = {
  schema_version: "2.0",
  diagram_type: "neural_network",
  nodes: [
    { id: "conv", label: "Conv", type: "module", group_id: "inner" },
    { id: "inner", label: "Inner", type: "group", group_id: "block" },
    { id: "block", label: "Block", type: "group", group_id: null },
    { id: "head", label: "Head", type: "output", group_id: null, bbox: [1, 2, 3, 4], confidence: 0.9 },
  ],
  edges: [
    { source: "conv", target: "head", relation: "depends_on", label: "skip", condition: "x > 0" },
  ],
};

describe("toFlow / fromFlow", () => {
  it("round-trips the spec example exactly", () => {
    const { nodes, edges } = toFlow(SPEC);

    expect(fromFlow(nodes, edges, SPEC.diagram_type)).toEqual(SPEC);
  });

  it("maps groups to parentId and group nodes, parents first", () => {
    const { nodes } = toFlow(NESTED);

    expect(nodes.map((n) => [n.id, n.type, n.parentId])).toEqual([
      ["block", "group", undefined],
      ["inner", "group", "block"],
      ["conv", "diagram", "inner"],
      ["head", "diagram", undefined],
    ]);
    expect(nodes[1].expandParent).toBe(true);
  });

  it("round-trips groups, metadata, and edge fields", () => {
    const { nodes, edges } = toFlow(NESTED);
    const back = fromFlow(nodes, edges, NESTED.diagram_type);

    const byId = (g: DiagramGraph) => Object.fromEntries(g.nodes.map((n) => [n.id, n]));
    expect(byId(back)).toEqual(byId(NESTED));
    expect(back.edges).toEqual(NESTED.edges);
  });
});

describe("edgeAppearance", () => {
  it("shows the label, falling back to the condition", () => {
    const base = { relation: "flows_to", label: null, condition: null };
    expect(edgeAppearance({ ...base, label: "Yes" }).label).toBe("Yes");
    expect(edgeAppearance({ ...base, condition: "x > 0" }).label).toBe("x > 0");
    expect(edgeAppearance(base).label).toBeUndefined();
  });

  it("names non-flow relations and dashes dependencies", () => {
    expect(edgeAppearance({ relation: "composes", label: "owns", condition: null }).label).toBe(
      "owns (composes)",
    );
    const dep = edgeAppearance({ relation: "depends_on", label: null, condition: null });
    expect(dep.label).toBe("depends on");
    expect(dep.style).toEqual({ strokeDasharray: "6 4" });
  });
});

describe("parentsFirst", () => {
  it("keeps an already valid order", () => {
    const nodes = [
      { id: "g", group_id: null },
      { id: "a", group_id: "g" },
      { id: "b", group_id: null },
    ];
    expect(parentsFirst(nodes)).toEqual(nodes);
  });

  it("terminates on a containment cycle", () => {
    const nodes = [
      { id: "a", group_id: "b" },
      { id: "b", group_id: "a" },
    ];
    expect(parentsFirst(nodes).map((n) => n.id).sort()).toEqual(["a", "b"]);
  });
});

describe("nextNodeId", () => {
  it("continues after the highest n<k> id", () => {
    expect(nextNodeId(["n1", "n7", "conv", "n3"])).toBe("n8");
    expect(nextNodeId([])).toBe("n1");
  });
});
