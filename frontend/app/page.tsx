"use client";
import Link from "next/link";
import { AlertsTable } from "@/components/AlertsTable";
import { COLORS, LineSeries } from "@/components/charts";
import { Async, Badge, Card, DataLabels, Notice, PageHeader, Stat } from "@/components/ui";
import { getBackend } from "@/lib/api";
import { fmtCI, fmtDate, fmtFixed, fmtNum, fmtPct } from "@/lib/format";
import { useAsync, useDataset } from "@/lib/hooks";
import type { DashboardData, Metrics } from "@/lib/types";

export default function DashboardPage() {
  const { dataset } = useDataset();
  const state = useAsync(async () => {
    const b = getBackend();
    const [d, m] = await Promise.all([b.dashboard(dataset), b.metrics(dataset)]);
    return { d, m, mode: b.mode };
  }, `dashboard:${dataset}`);
  return (
    <>
      <PageHeader
        title="Analyst dashboard"
        subtitle="Backtest of a capacity-constrained alert queue on held-out days of synthetic data. Every figure below is computed from a recorded experiment run."
        right={<DataLabels demo={state.status === "success" && state.data.mode === "demo"} />}
      />
      <Async state={state} label="Loading dashboard">{({ d, m }) => <View d={d} m={m} />}</Async>
    </>
  );
}

function View({ d, m }: { d: DashboardData; m: Metrics }) {
  const s = d.summary;
  const p = s.primary;
  const main = m.h1.models["M3_lgbm_TBG"].test.strict;
  const cal = m.h1.calibration["M3_lgbm_TBG"];
  const skill = 1 - cal.brier / cal.brier_baseline_prevalence;
  const overNominal = p.miss_ci95 ? p.miss_ci95[1] > p.policy.alpha && p.realised_miss_rate > p.policy.alpha : false;
  const series = s.series.day.map((_, i) => ({ date: s.series.date[i], Review: s.series.review[i], Backlog: s.series.backlog[i], "Auto-closed": s.series.auto_close[i], Expired: s.series.expired[i] }));
  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Cases scored (test window)" value={fmtNum(s.counts.test_strict_cases, 0)} hint={`${fmtDate(s.split.test.dates[0])} – ${fmtDate(s.split.test.dates[1])}`} />
        <Stat label="Review queue" value={fmtNum(p.n_review_total, 0)} hint={`${fmtNum(p.avg_review_per_day, 1)} cases per day`} />
        <Stat label="Review capacity" value={`${fmtNum(p.avg_review_per_day, 1)} / day`} hint={`m = ${p.capacity_multiplier} × training prevalence`} />
        <Stat label="Backlog (mean / max)" value={`${fmtNum(p.mean_backlog, 0)} / ${fmtNum(p.max_backlog, 0)}`} hint={`mean age ${fmtFixed(p.mean_backlog_age, 1)} days`} />
        <Stat label="Auto-closed cases" value={fmtNum(p.auto_closed_cases, 0)} hint={`${fmtPct(p.auto_closed_cases / p.n_cases, 1)} of cases · policy ${p.policy.kind}, α = ${fmtPct(p.policy.alpha, 0)}`} />
        <Stat label="Realised miss rate (auto-closed)" value={fmtPct(p.realised_miss_rate)} tone={overNominal ? "danger" : undefined} hint={`95 % CI ${fmtCI(p.miss_ci95)} · ${p.n_clusters ?? "?"} schemes · nominal ${fmtPct(p.policy.alpha, 0)}`} />
        <Stat label="Positives never reviewed" value={fmtPct(1 - p.review_recall)} tone="warn" hint={`review recall ${fmtPct(p.review_recall)} — limited by capacity`} />
        <Stat label="Model health (PR-AUC)" value={fmtFixed(main.pr_auc.mean, 3)} hint={`Brier skill vs prevalence baseline ${fmtPct(skill, 1)} · modest`} />
      </dl>
      <Notice tone="warn" title="Read with care:">
        {p.n_positives} positive cases from only {p.n_clusters ?? "?"} independent laundering schemes. Miss-rate intervals are wide; realised miss rate counts auto-closed positives only — positives that
        expire unreviewed in the backlog ({fmtPct(p.expired_positive_rate)}) are a separate, larger loss.
      </Notice>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Daily queue and backlog" subtitle="Cases entering REVIEW and open backlog per day (primary policy)">
          <LineSeries data={series} xKey="date" xFormat={(v) => fmtDate(String(v))} yFormat={(v) => fmtNum(v, 0)} ariaLabel="Line chart of daily review count and backlog size" series={[{ key: "Review", label: "Review", color: COLORS.blue }, { key: "Backlog", label: "Backlog", color: COLORS.amber }]} />
        </Card>
        <Card title="Auto-closed and expired per day" subtitle="AUTO-CLOSE removes low-score cases; EXPIRED = unreviewed after the backlog limit">
          <LineSeries data={series} xKey="date" xFormat={(v) => fmtDate(String(v))} yFormat={(v) => fmtNum(v, 0)} ariaLabel="Line chart of daily auto-closed and expired cases" series={[{ key: "Auto-closed", label: "Auto-closed", color: COLORS.teal }, { key: "Expired", label: "Expired", color: COLORS.red }]} />
        </Card>
      </div>
      <Card title="Latest alerts" subtitle={`${s.queue_sample.rule}. Showing a sample of ${s.queue_sample.n} of ${fmtNum(s.queue_sample.of_total_review, 0)} REVIEW cases.`} actions={<Link href="/alerts" className="text-sm font-medium text-[#1E3A5F] hover:underline">All alerts →</Link>}>
        <AlertsTable items={d.latest_alerts} caption="Latest alerts" />
      </Card>
      <Card title="Analyst feedback (simulated)" subtitle="Decisions recorded in this demo session">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge tone="info">SIMULATED FEEDBACK</Badge>
          <span>{d.decisions.decided_in_sample} of {d.decisions.sample_size} sampled alerts decided ·</span>
          {Object.entries(d.decisions.by_decision).map(([k, v]) => <Badge key={k}>{k.replace("_", " ")}: {v}</Badge>)}
        </div>
      </Card>
    </div>
  );
}
