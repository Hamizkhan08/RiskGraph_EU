"use client";
import Link from "next/link";
import { fmtDateTime, fmtNum, fmtPct, fmtFixed, PRIORITY_LABEL, STATUS_LABEL } from "@/lib/format";
import type { Alert } from "@/lib/types";
import { Badge, PRIORITY_TONE, STATUS_TONE, Td, TableWrap, Th } from "./ui";

export function NetworkIndicator({ a }: { a: Alert }) {
  const n = a.network;
  const cyc = n.cycles.c2 + n.cycles.c3 + n.cycles.c4 > 0;
  return (
    <div className="flex flex-wrap items-center gap-1 text-xs" style={{ color: "var(--slate-gray)" }}>
      <span>deg {fmtNum(n.degree_7d, 0)} · 2-hop {fmtNum(n.reach2_7d, 0)}</span>
      {cyc && <Badge tone="warn">cycle</Badge>}
      {n.fanin_burst_3d >= 5 && <Badge tone="warn">fan-in</Badge>}
      {n.fanout_burst_3d >= 5 && <Badge tone="warn">fan-out</Badge>}
    </div>
  );
}

/* Mini score bar — warm palette */
function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, score * 100);
  const trackColor = "rgba(20,20,19,0.08)";
  const fillColor = pct > 70
    ? "var(--signal-orange)"      /* danger — Signal Orange */
    : pct > 40
      ? "var(--light-orange)"     /* warn — Light Signal Orange */
      : "var(--link-blue)";       /* safe — Link Blue */

  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 500, color: "var(--ink-black)", fontVariantNumeric: "tabular-nums" }}>
        {fmtFixed(score, 3)}
      </div>
      <div style={{ marginTop: 4, height: 3, background: trackColor, borderRadius: 99, width: 56, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: fillColor, borderRadius: 99 }} />
      </div>
    </div>
  );
}

export function AlertsTable({ items, caption }: { items: Alert[]; caption: string }) {
  return (
    <TableWrap caption={caption}>
      <thead>
        <tr>
          <Th>Case ID</Th>
          <Th>Decision time (UTC)</Th>
          <Th className="text-right">Risk score</Th>
          <Th>Priority</Th>
          <Th>Status</Th>
          <Th>Key reason</Th>
          <Th>Network</Th>
          <Th className="text-right">Amounts, 7 days (nominal)</Th>
        </tr>
      </thead>
      <tbody>
        {items.map((a) => {
          const isP1 = a.priority === "P1";
          return (
            <tr
              key={a.id}
              style={{
                background: isP1 ? "rgba(207,69,0,0.03)" : "var(--lifted-cream)",
                transition: "background 0.12s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  isP1 ? "rgba(207,69,0,0.07)" : "var(--soft-bone)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.background =
                  isP1 ? "rgba(207,69,0,0.03)" : "var(--lifted-cream)";
              }}
            >
              <Td>
                <Link
                  href={`/alerts/${a.id}`}
                  className="font-mono text-xs font-medium underline-offset-2 hover:underline"
                  style={{ color: "var(--link-blue)" }}
                >
                  {a.id}
                </Link>
              </Td>
              <Td className="whitespace-nowrap" style={{ color: "var(--slate-gray)", fontSize: 12 }}>
                {fmtDateTime(a.decision_timestamp)}
              </Td>
              <Td className="text-right">
                <ScoreBar score={a.score} />
                <div className="text-xs mt-0.5" style={{ color: "var(--slate-gray)" }} title="Platt-calibrated">
                  est. {fmtPct(a.p_cal, 1)}
                </div>
              </Td>
              <Td><Badge tone={PRIORITY_TONE[a.priority]}>{PRIORITY_LABEL[a.priority]}</Badge></Td>
              <Td><Badge tone={STATUS_TONE[a.status]}>{STATUS_LABEL[a.status]}</Badge></Td>
              <Td className="max-w-[14rem]" style={{ color: "var(--slate-gray)", fontSize: 12 }}>{a.key_reason}</Td>
              <Td><NetworkIndicator a={a} /></Td>
              <Td className="text-right whitespace-nowrap" style={{ fontSize: 12 }}>
                <div style={{ color: "var(--ink-black)", fontVariantNumeric: "tabular-nums" }}>out {fmtNum(a.amounts.out_7d, 0)}</div>
                <div style={{ color: "var(--slate-gray)", fontVariantNumeric: "tabular-nums" }}>in {fmtNum(a.amounts.in_7d, 0)}</div>
              </Td>
            </tr>
          );
        })}
      </tbody>
    </TableWrap>
  );
}
