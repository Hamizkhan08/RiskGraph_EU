import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NetworkGraph, computeLayout } from "@/components/NetworkGraph";
import type { GEdge, GNode } from "@/lib/types";

const nodes: GNode[] = [
  { id: "account_1", focal: true, n: 5, amount: 1000 },
  ...Array.from({ length: 9 }, (_, i) => ({ id: `account_${i + 2}`, focal: false, n: 1 + i, amount: 100 * (i + 1) })),
];
const edges: GEdge[] = nodes.slice(1).map((n, i) => ({ source: i % 2 ? n.id : "account_1", target: i % 2 ? "account_1" : n.id, n: 1, amount: n.amount, first: "2025-10-10T09:00:00", last: "2025-10-11T09:00:00" }));

describe("network layout", () => {
  it("is deterministic and keeps every node inside the canvas", () => {
    const a = computeLayout(nodes, edges, 420);
    const b = computeLayout(nodes, edges, 420);
    expect([...a.entries()]).toEqual([...b.entries()]);
    for (const { x, y } of a.values()) {
      expect(Number.isFinite(x) && Number.isFinite(y)).toBe(true);
      expect(x).toBeGreaterThanOrEqual(30);
      expect(x).toBeLessThanOrEqual(690);
      expect(y).toBeGreaterThanOrEqual(30);
      expect(y).toBeLessThanOrEqual(390);
    }
  });
  it("ignores edges that reference unknown nodes", () => {
    const pos = computeLayout(nodes, [...edges, { ...edges[0], source: "ghost", target: "account_1" }], 420);
    expect(pos.has("ghost")).toBe(false);
  });
});

describe("NetworkGraph", () => {
  it("hides flows below the minimum amount and unconnected counterparties, always keeping the focal node", () => {
    const { container, rerender } = render(<NetworkGraph nodes={nodes} edges={edges} minAmount={0} />);
    const visibleFlows = () => container.querySelectorAll('line[marker-end]').length;
    expect(visibleFlows()).toBe(9);
    rerender(<NetworkGraph nodes={nodes} edges={edges} minAmount={600} />);
    expect(visibleFlows()).toBe(4);              // amounts 600..900
    const labels = [...container.querySelectorAll("text")].map((t) => t.textContent);
    expect(labels).toContain("A·1");             // focal stays
    expect(labels).not.toContain("A·2");         // amount 100 hidden
  });
  it("exposes nodes and flows to assistive technology", () => {
    const { getAllByRole } = render(<NetworkGraph nodes={nodes} edges={edges} />);
    expect(getAllByRole("button", { name: /Focal account account_1/ })).toHaveLength(1);
    expect(getAllByRole("button", { name: /Transfer flow from/ }).length).toBe(9);
  });
});
