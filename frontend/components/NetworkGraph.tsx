"use client";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type SimulationNodeDatum } from "d3-force";
import { useMemo } from "react";
import { fmtDateTime, fmtNum } from "@/lib/format";
import type { GEdge, GNode } from "@/lib/types";
import { cn } from "./ui";

export type Selection = { type: "node"; id: string } | { type: "edge"; id: string } | null;
const W = 720;
const edgeId = (e: GEdge) => `${e.source}→${e.target}`;
interface LNode extends SimulationNodeDatum {
  id: string;
}
export const shortId = (id: string) => id.replace("account_", "A·").replace("individual_", "I·").replace("business_", "B·");

export function computeLayout(nodes: GNode[], edges: GEdge[], h: number): Map<string, { x: number; y: number }> {
  const ns: LNode[] = nodes.map((n, i) => ({ id: n.id, x: W / 2 + Math.cos(i * 2.4) * (40 + i * 7), y: h / 2 + Math.sin(i * 2.4) * (30 + i * 5) }));
  const ids = new Set(ns.map((n) => n.id));
  const links = edges.filter((e) => ids.has(e.source) && ids.has(e.target)).map((e) => ({ source: e.source, target: e.target }));
  const sim = forceSimulation(ns)
    .force("link", forceLink<LNode, { source: string; target: string }>(links).id((d) => d.id).distance(95))
    .force("charge", forceManyBody().strength(-280))
    .force("center", forceCenter(W / 2, h / 2))
    .force("collide", forceCollide(26))
    .stop();
  for (let i = 0; i < 250; i++) sim.tick();
  const pad = 30;
  return new Map(ns.map((n) => [n.id, { x: Math.min(W - pad, Math.max(pad, n.x ?? W / 2)), y: Math.min(h - pad, Math.max(pad, n.y ?? h / 2)) }]));
}

export function NetworkGraph({ nodes, edges, height = 420, showLabels = true, minAmount = 0, selected = null, onSelect, ariaLabel = "Transaction network around the focal account" }: {
  nodes: GNode[];
  edges: GEdge[];
  height?: number;
  showLabels?: boolean;
  minAmount?: number;
  selected?: Selection;
  onSelect?: (s: Selection) => void;
  ariaLabel?: string;
}) {
  const pos = useMemo(() => computeLayout(nodes, edges, height), [nodes, edges, height]);
  const maxAmt = Math.max(1, ...edges.map((e) => e.amount));
  const maxNode = Math.max(1, ...nodes.map((n) => n.amount));
  const visEdges = edges.filter((e) => e.amount >= minAmount && pos.has(e.source) && pos.has(e.target));
  const connected = new Set(visEdges.flatMap((e) => [e.source, e.target]));
  const visNodes = nodes.filter((n) => n.focal || connected.has(n.id) || minAmount === 0);
  const r = (n: GNode) => (n.focal ? 16 : 7 + 9 * Math.sqrt(n.amount / maxNode));
  return (
    <svg viewBox={`0 0 ${W} ${height}`} className="w-full rounded-md border border-slate-200 bg-slate-50" role="group" aria-label={ariaLabel} style={{ height }}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="#64748B" />
        </marker>
      </defs>
      {visEdges.map((e) => {
        const a = pos.get(e.source)!;
        const b = pos.get(e.target)!;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        const tr = r(nodes.find((n) => n.id === e.target)!) + 2;
        const sel = selected?.type === "edge" && selected.id === edgeId(e);
        return (
          <g key={edgeId(e)}>
            <line x1={a.x} y1={a.y} x2={b.x - (dx / len) * tr} y2={b.y - (dy / len) * tr} stroke={sel ? "#1E3A5F" : "#94A3B8"} strokeWidth={1 + 4 * Math.sqrt(e.amount / maxAmt)} markerEnd="url(#arrow)" opacity={sel ? 1 : 0.8} />
            <line
              x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="transparent" strokeWidth={12} tabIndex={0} role="button" className="cursor-pointer focus-visible:outline-none"
              aria-label={`Transfer flow from ${e.source} to ${e.target}: ${e.n} transactions, ${fmtNum(e.amount)} nominal units`}
              onClick={() => onSelect?.({ type: "edge", id: edgeId(e) })}
              onKeyDown={(ev) => ev.key === "Enter" && onSelect?.({ type: "edge", id: edgeId(e) })}
            />
          </g>
        );
      })}
      {visNodes.map((n) => {
        const p = pos.get(n.id)!;
        const sel = selected?.type === "node" && selected.id === n.id;
        return (
          <g key={n.id} transform={`translate(${p.x},${p.y})`} tabIndex={0} role="button" className="cursor-pointer outline-none focus-visible:[&>circle]:stroke-amber-500" aria-label={`${n.focal ? "Focal account" : "Counterparty"} ${n.id}: ${n.n} transactions`} onClick={() => onSelect?.({ type: "node", id: n.id })} onKeyDown={(ev) => ev.key === "Enter" && onSelect?.({ type: "node", id: n.id })}>
            <circle r={r(n)} fill={n.focal ? "#1E3A5F" : "#64748B"} stroke={sel ? "#B7791F" : "#fff"} strokeWidth={sel ? 3 : 1.5} />
            {showLabels && (
              <text y={r(n) + 12} textAnchor="middle" fontSize={10} fill="#334155" className="pointer-events-none select-none">
                {shortId(n.id)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export function NetworkLegend() {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-600" aria-label="Legend">
      <li className="flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-full bg-[#1E3A5F]" /> Focal account</li>
      <li className="flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-full bg-slate-500" /> Counterparty (size ∝ amount)</li>
      <li className="flex items-center gap-1.5"><span className="inline-block h-0.5 w-6 bg-slate-400" /> Flow, arrow = direction (width ∝ amount)</li>
      <li>A· account · I· individual · B· business</li>
    </ul>
  );
}

export function NetworkDetails({ selection, nodes, edges, className }: { selection: Selection; nodes: GNode[]; edges: GEdge[]; className?: string }) {
  if (!selection) return <p className={cn("text-sm text-slate-500", className)}>Select a node or a flow to see its details.</p>;
  if (selection.type === "node") {
    const n = nodes.find((x) => x.id === selection.id);
    if (!n) return null;
    const inn = edges.filter((e) => e.target === n.id);
    const out = edges.filter((e) => e.source === n.id);
    return (
      <dl className={cn("grid grid-cols-2 gap-x-4 gap-y-1 text-sm", className)}>
        <dt className="text-slate-500">Account</dt><dd className="font-mono">{n.id}</dd>
        <dt className="text-slate-500">Role</dt><dd>{n.focal ? "Focal account" : "Counterparty"}</dd>
        <dt className="text-slate-500">Transactions (window)</dt><dd>{fmtNum(n.n, 0)}</dd>
        <dt className="text-slate-500">Amount (nominal)</dt><dd>{fmtNum(n.amount)}</dd>
        <dt className="text-slate-500">Flows in / out (shown)</dt><dd>{inn.length} / {out.length}</dd>
      </dl>
    );
  }
  const e = edges.find((x) => edgeId(x) === selection.id);
  if (!e) return null;
  return (
    <dl className={cn("grid grid-cols-2 gap-x-4 gap-y-1 text-sm", className)}>
      <dt className="text-slate-500">From</dt><dd className="font-mono">{e.source}</dd>
      <dt className="text-slate-500">To</dt><dd className="font-mono">{e.target}</dd>
      <dt className="text-slate-500">Transactions</dt><dd>{e.n}</dd>
      <dt className="text-slate-500">Amount (nominal)</dt><dd>{fmtNum(e.amount)}</dd>
      <dt className="text-slate-500">First</dt><dd>{fmtDateTime(e.first)}</dd>
      <dt className="text-slate-500">Last</dt><dd>{fmtDateTime(e.last)}</dd>
    </dl>
  );
}
