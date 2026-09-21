"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { NetworkGraph } from "@/components/NetworkGraph";
import { Async, Badge, Card, ErrorState, Notice, PageHeader, PRIORITY_TONE, STATUS_TONE, Td, TableWrap, Th } from "@/components/ui";
import { getBackend } from "@/lib/api";
import { fmtDateTime, fmtFixed, fmtMoney, fmtNum, fmtPct, parseTs, PRIORITY_LABEL, STATUS_LABEL } from "@/lib/format";
import { useAsync } from "@/lib/hooks";
import type { CaseDetail, Contribution, Decision } from "@/lib/types";

export default function CasePage() {
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(params.id);
  const state = useAsync(async () => ({ c: await getBackend().caseDetail(id), mode: getBackend().mode }), `case:${id}`);
  return (
    <>
      <p className="mb-3 text-sm"><Link href="/alerts" className="text-[#1E3A5F] hover:underline">← Back to alerts</Link></p>
      <Async state={state} label="Loading case">{({ c, mode }) => <CaseView c={c} demo={mode === "demo"} onChanged={state.reload} />}</Async>
    </>
  );
}

function ContributionBars({ items }: { items: Contribution[] }) {
  const max = Math.max(...items.map((i) => Math.abs(i.contribution)), 1e-9);
  return (
    <ul className="space-y-2" aria-label="Top feature contributions (log-odds)">
      {items.map((f) => (
        <li key={f.feature} className="grid grid-cols-[minmax(0,12rem)_1fr_4.5rem] items-center gap-2 text-sm">
          <span className="truncate font-mono text-xs" title={f.definition}>{f.feature}</span>
          <span className="relative h-3 rounded bg-slate-100" aria-hidden>
            <span className={`absolute top-0 h-3 rounded ${f.contribution >= 0 ? "left-1/2 bg-[#B4443C]" : "right-1/2 bg-[#2F7D5B]"}`} style={{ width: `${(Math.abs(f.contribution) / max) * 50}%` }} />
            <span className="absolute left-1/2 top-0 h-3 w-px bg-slate-400" />
          </span>
          <span className="text-right tabular-nums">{f.contribution >= 0 ? "+" : "−"}{fmtFixed(Math.abs(f.contribution), 2)}</span>
          <span className="col-span-3 -mt-1 pl-1 text-[11px] text-slate-500">value {fmtNum(f.value, 2)} · {f.definition}</span>
        </li>
      ))}
    </ul>
  );
}

function CaseView({ c, demo, onChanged }: { c: CaseDetail; demo: boolean; onChanged: () => void }) {
  const [note, setNote] = useState("");
  const [analyst, setAnalyst] = useState("demo-analyst");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<Error | null>(null);
  const [done, setDone] = useState<Decision | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const ev = c.evidence;
  const submit = async (decision: Decision) => {
    setBusy(true);
    setErr(null);
    try {
      await getBackend().decide(c.id, { decision, note, analyst });
      setDone(decision);
      setNote("");
      onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setBusy(false);
    }
  };
  type Ev = { t: number; label: string; detail: string };
  const timeline: Ev[] = [
    ...ev.transactions.map((t) => ({ t: parseTs(t.timestamp).getTime(), label: fmtDateTime(t.timestamp), detail: `${t.direction === "out" ? "Sent to" : "Received from"} ${t.direction === "out" ? t.dst : t.src} — ${t.type}, ${fmtMoney(t.amount, t.currency)}` })),
    ...(c.decision_history ?? []).map((h) => ({ t: parseTs(h.created_at).getTime(), label: fmtDateTime(h.created_at), detail: `Analyst decision: ${STATUS_LABEL[h.decision]}${h.simulated ? " (simulated)" : ""}` })),
  ].sort((a, b) => a.t - b.t);
  return (
    <div className="space-y-5">
      <PageHeader
        title={c.id}
        subtitle={<>Account <span className="font-mono">{c.account}</span> · decision timestamp {fmtDateTime(c.decision_timestamp)} UTC. Evidence shows only activity available at that moment.</>}
        right={<div className="flex gap-2"><Badge tone={PRIORITY_TONE[c.priority]}>{PRIORITY_LABEL[c.priority]}</Badge><Badge tone={STATUS_TONE[c.status]}>{STATUS_LABEL[c.status]}</Badge></div>}
      />
      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Card title="Risk assessment" subtitle="Model output on synthetic data — an elevated-risk signal, not a finding of wrongdoing">
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div><dt className="text-xs uppercase tracking-wide text-slate-500">Risk score</dt><dd className="text-2xl font-semibold tabular-nums">{fmtFixed(c.score, 3)}</dd></div>
              <div><dt className="text-xs uppercase tracking-wide text-slate-500">Calibrated estimate</dt><dd className="text-2xl font-semibold tabular-nums">{fmtPct(c.p_cal, 1)}</dd></div>
              <div><dt className="text-xs uppercase tracking-wide text-slate-500">Key reason</dt><dd className="text-sm font-medium">{c.key_reason}</dd></div>
            </dl>
            <p className="mt-3 text-xs text-slate-500">The calibrated estimate is fitted on a validation window of synthetic data and is best read as relative risk; it is not the probability that any offence occurred.</p>
          </Card>
          <Card title="Why this case was prioritised" subtitle="Exact TreeSHAP attributions of the model (log-odds; red raises risk, green lowers it)">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Grouped reasons</h3>
            <ul className="mb-4 flex flex-wrap gap-2" aria-label="Reason codes">
              {c.explanation.reasons.map((r) => (
                <li key={r.code}><Badge tone={r.contribution >= 0 ? "danger" : "success"} title={r.code}>{r.label} ({r.contribution >= 0 ? "+" : "−"}{fmtFixed(Math.abs(r.contribution), 2)})</Badge></li>
              ))}
            </ul>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Top feature contributions</h3>
            <ContributionBars items={c.explanation.top_features} />
          </Card>
          <Card title="Transaction evidence" subtitle={`Largest ${ev.transactions.length} of ${fmtNum(ev.n_transactions_window, 0)} transactions in the ${ev.lookback_days} days up to the decision timestamp`}>
            <TableWrap caption="Transaction evidence">
              <thead><tr><Th>Time (UTC)</Th><Th>Direction</Th><Th>Counterparty</Th><Th>Type</Th><Th className="text-right">Amount</Th></tr></thead>
              <tbody>
                {ev.transactions.map((t, i) => (
                  <tr key={i}>
                    <Td className="whitespace-nowrap">{fmtDateTime(t.timestamp)}</Td>
                    <Td><Badge tone={t.direction === "out" ? "warn" : "info"}>{t.direction === "out" ? "Outgoing" : "Incoming"}</Badge></Td>
                    <Td className="font-mono text-xs">{t.direction === "out" ? t.dst : t.src}</Td>
                    <Td>{t.type}</Td>
                    <Td className="text-right">{fmtMoney(t.amount, t.currency)}</Td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
          </Card>
          <Card title="Timeline" subtitle="Evidence transactions and analyst decisions in time order">
            {timeline.length === 0 ? <p className="text-sm text-slate-500">No events.</p> : (
              <ol className="relative space-y-3 border-l border-slate-200 pl-4">
                {timeline.map((e, i) => (
                  <li key={i} className="text-sm"><span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white bg-[#3B6EA8]" aria-hidden /><time className="block text-xs text-slate-500">{e.label}</time>{e.detail}</li>
                ))}
              </ol>
            )}
          </Card>
        </div>
        <div className="space-y-5">
          <Card title="Analyst decision" subtitle={demo ? "Feedback is simulated and stored only in this browser" : "Recorded by the API with an audit event"}>
            {demo && <div className="mb-3"><Badge tone="info">SIMULATED FEEDBACK</Badge></div>}
            <label className="mb-2 block text-xs font-medium text-slate-600">Analyst
              <input value={analyst} onChange={(e) => setAnalyst(e.target.value.replace(/[^A-Za-z0-9 ._-]/g, ""))} maxLength={40} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
            </label>
            <label className="mb-3 block text-xs font-medium text-slate-600">Note (optional, max 500 characters)
              <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} rows={3} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm" />
            </label>
            <div className="flex flex-col gap-2" role="group" aria-label="Record a decision">
              <button disabled={busy} onClick={() => submit("suspicious")} className="rounded bg-[#B4443C] px-3 py-2 text-sm font-medium text-white hover:bg-[#9c3932] disabled:opacity-50">Suspicious</button>
              <button disabled={busy} onClick={() => submit("false_positive")} className="rounded bg-[#2F7D5B] px-3 py-2 text-sm font-medium text-white hover:bg-[#276a4d] disabled:opacity-50">False positive</button>
              <button disabled={busy} onClick={() => submit("requires_review")} className="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-50">Requires review</button>
            </div>
            <div aria-live="polite" className="mt-3 text-sm">
              {done && <p role="status" className="text-emerald-800">Decision recorded: {STATUS_LABEL[done]}{demo ? " (simulated feedback)" : ""}.</p>}
              {err && <ErrorState error={err} />}
            </div>
          </Card>
          <Card title="Decision history">
            {(c.decision_history ?? []).length === 0 ? <p className="text-sm text-slate-500">No decisions recorded yet.</p> : (
              <ul className="space-y-2 text-sm">
                {(c.decision_history ?? []).map((h, i) => (
                  <li key={i}><Badge tone={STATUS_TONE[h.decision]}>{STATUS_LABEL[h.decision]}</Badge> <span className="text-slate-500">{fmtDateTime(h.created_at)} · {h.analyst}{h.simulated ? " · simulated" : ""}</span>{h.note && <p className="mt-0.5 text-slate-700">{h.note}</p>}</li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Network context" actions={<Link href={`/network?case=${c.id}`} className="text-sm font-medium text-[#1E3A5F] hover:underline">Open full view →</Link>}>
            <NetworkGraph nodes={ev.nodes} edges={ev.edges} height={260} showLabels={false} selected={sel ? { type: "node", id: sel } : null} onSelect={(s) => setSel(s?.type === "node" ? s.id : null)} ariaLabel="Compact transaction network" />
            <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              <dt className="text-slate-500">Counterparties (7 d)</dt><dd>{fmtNum(c.network.degree_7d, 0)}</dd>
              <dt className="text-slate-500">Accounts within 2 hops</dt><dd>{fmtNum(c.network.reach2_7d, 0)}</dd>
              <dt className="text-slate-500">Hub neighbours</dt><dd>{fmtPct(c.network.hub_neighbour_share, 0)}</dd>
              <dt className="text-slate-500">Closed loops (2/3/4)</dt><dd>{c.network.cycles.c2} / {c.network.cycles.c3} / {c.network.cycles.c4}</dd>
            </dl>
          </Card>
          <Card title="Research annotation">
            <details>
              <summary className="cursor-pointer text-sm font-medium text-[#1E3A5F]">Show synthetic ground truth (research view)</summary>
              <div className="mt-2 space-y-1 text-sm">
                <Notice tone="warn">Ground truth from the data generator. It is never a model input and is not available to a real analyst.</Notice>
                <p>Generator label: <strong>{c.research.ground_truth_positive ? "part of a planted scheme" : "background activity"}</strong></p>
                {c.research.family && <p>Scheme family: {c.research.family}</p>}
                {c.research.scheme_id && <p>Scheme: <span className="font-mono text-xs">{c.research.scheme_id}</span></p>}
              </div>
            </details>
          </Card>
        </div>
      </div>
    </div>
  );
}
