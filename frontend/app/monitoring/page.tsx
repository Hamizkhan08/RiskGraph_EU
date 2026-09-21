"use client";
import { BarSeries, COLORS, LineSeries } from "@/components/charts";
import { Async, Badge, Card, DataLabels, Notice, PageHeader, Td, TableWrap, Th, cn } from "@/components/ui";
import { getBackend } from "@/lib/api";
import { fmtDate, fmtFixed, fmtNum, fmtPct } from "@/lib/format";
import { useAsync, useDataset } from "@/lib/hooks";
import type { DataQuality, Monitoring } from "@/lib/types";

export default function MonitoringPage() {
  const { dataset } = useDataset();
  const state = useAsync(async () => {
    const b = getBackend();
    const [mon, dq] = await Promise.all([b.monitoring(dataset), b.dataQuality(dataset)]);
    return { mon, dq, mode: b.mode };
  }, `monitoring:${dataset}`);
  return (
    <>
      <PageHeader title="Monitoring" subtitle="Score, volume, drift and calibration over time. This is a backtest replay of held-out days — observed on synthetic data — not live monitoring of a production system." right={<div className="flex gap-2"><Badge tone="brand">BACKTEST REPLAY</Badge><DataLabels demo={state.status === "success" && state.data.mode === "demo"} /></div>} />
      <Async state={state} label="Loading monitoring">{({ mon, dq }) => <View mon={mon} dq={dq} />}</Async>
    </>
  );
}

const psiTone = (v: number) => (v >= 0.25 ? "bg-red-100 text-red-900" : v >= 0.1 ? "bg-amber-100 text-amber-900" : "");

function View({ mon, dq }: { mon: Monitoring; dq: DataQuality }) {
  const weekly = mon.weekly.map((w) => ({ week: fmtDate(w.week_start), Reviews: w.n_review_at_m1, Positives: w.n_pos, Mean: w.mean_p_cal, p90: w.p90, p99: w.p99, Recall: w.recall_at_m1, block: w.block }));
  return (
    <div className="space-y-4">
      <Notice tone="info" title="What is observed here:">{mon.mode}. {mon.score_definition}. Weeks with fewer than 100 cases are omitted; recall is undefined in weeks without positives.</Notice>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Alert volume per week" subtitle="Reviews at the primary capacity (m = 1) and positive cases (validation weeks first, then test)">
          <BarSeries data={weekly} xKey="week" yFormat={(v) => fmtNum(v, 0)} ariaLabel="Weekly review volume and positive cases" series={[{ key: "Reviews", label: "Reviews (m=1)", color: COLORS.blue }, { key: "Positives", label: "Positive cases", color: COLORS.red }]} />
        </Card>
        <Card title="Score distribution per week" subtitle="Calibrated probability: mean, 90th and 99th percentile">
          <LineSeries data={weekly} xKey="week" yFormat={(v) => fmtPct(v, 2)} ariaLabel="Weekly calibrated score mean and upper percentiles" series={[{ key: "Mean", label: "Mean", color: COLORS.slate }, { key: "p90", label: "p90", color: COLORS.blue }, { key: "p99", label: "p99", color: COLORS.navy }]} />
        </Card>
        <Card title="Recall at the review capacity per week" subtitle="Share of the week's positive cases inside the daily top-K (all positives, including continuing schemes)">
          <LineSeries data={weekly} xKey="week" yFormat={(v) => fmtPct(v, 0)} yDomain={[0, 1]} ariaLabel="Weekly recall at capacity" series={[{ key: "Recall", label: "Recall@K", color: COLORS.teal }]} />
        </Card>
        <Card title="Calibration by 4-week window" subtitle="Deterioration shows as observed rate drifting from the mean prediction">
          <TableWrap caption="Calibration by window">
            <thead><tr><Th>Window from</Th><Th className="text-right">Positives</Th><Th className="text-right">Brier ·10⁻³</Th><Th className="text-right">ECE ·10⁻³</Th><Th className="text-right">Mean prediction</Th><Th className="text-right">Observed rate</Th></tr></thead>
            <tbody>{mon.calibration_windows.map((c) => <tr key={c.window_start}><Td>{fmtDate(c.window_start)}</Td><Td className="text-right">{c.n_pos}</Td><Td className="text-right">{fmtFixed(c.brier * 1000, 3)}</Td><Td className="text-right">{fmtFixed(c.ece * 1000, 3)}</Td><Td className="text-right">{fmtPct(c.mean_pred, 3)}</Td><Td className="text-right">{fmtPct(c.obs_rate, 3)}</Td></tr>)}</tbody>
          </TableWrap>
        </Card>
      </div>
      <Card title="Feature drift (population stability index)" subtitle={`${mon.psi_note}. Reference = training block. Highlighted: ≥ 0.10 amber, ≥ 0.25 red (values always shown).`}>
        <TableWrap caption="Feature drift PSI by window">
          <thead><tr><Th>Feature</Th>{mon.feature_drift.map((d) => <Th key={d.window_start} className="text-right">{fmtDate(d.window_start)}</Th>)}</tr></thead>
          <tbody>{mon.top_features.map((f) => <tr key={f}><Td className="font-mono text-xs">{f}</Td>{mon.feature_drift.map((d) => <Td key={d.window_start} className={cn("text-right", psiTone(d.psi[f]))}>{fmtFixed(d.psi[f], 3)}</Td>)}</tr>)}</tbody>
        </TableWrap>
      </Card>
      <Card title="Data quality" subtitle="Validation report of the generated transaction file">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
          {[["Transactions (in period)", fmtNum(dq.in_period_rows, 0)], ["Positive transactions", `${fmtNum(dq.positive_transactions, 0)} (${fmtPct(dq.positive_prevalence_tx, 3)})`], ["Accounts", fmtNum(dq.n_accounts, 0)], ["Schemes", fmtNum(dq.schemes_total, 0)], ["Rows after period end", `${dq.post_period_rows} (${dq.post_period_positive_rows} positive)`], ["Duplicate rows", fmtNum(dq.duplicate_rows, 0)], ["Self-loops", fmtNum(dq.self_loops, 0)], ["Scheme duration p50 / p95", `${fmtFixed(dq.scheme_duration_days.p50, 0)} / ${fmtFixed(dq.scheme_duration_days.p95, 0)} days`]].map(([k, v]) => <div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd className="font-medium">{v}</dd></div>)}
        </dl>
        {dq.warnings.length > 0 && <ul className="mt-3 space-y-1">{dq.warnings.map((w) => <li key={w}><Notice tone="warn">{w}</Notice></li>)}</ul>}
      </Card>
    </div>
  );
}
