"use client";
import * as Tabs from "@radix-ui/react-tabs";
import { useState } from "react";
import { BarSeries, COLORS, LineSeries } from "@/components/charts";
import { Async, Badge, Card, DataLabels, Notice, PageHeader, Td, TableWrap, Th, cn } from "@/components/ui";
import { getBackend } from "@/lib/api";
import { fmtCI, fmtFixed, fmtNum, fmtPct } from "@/lib/format";
import { useAsync, useDataset } from "@/lib/hooks";
import type { Contrast, HeldoutCell, Metrics, SimCell } from "@/lib/types";

const ORDER = ["M1_logreg_TB", "M2_lgbm_TB", "M3_lgbm_TBG", "M4_lgbm_TBGM", "A1_lgbm_T", "A2_lgbm_TBG_notype"];
const SHORT: Record<string, string> = {
  M1_logreg_TB: "M1 Logistic (T+B)", M2_lgbm_TB: "M2 GBM (T+B)", M3_lgbm_TBG: "M3 GBM + graph (T+B+G)", M4_lgbm_TBGM: "M4 + motifs (T+B+G+M)",
  A1_lgbm_T: "A1 own activity only (T)", A2_lgbm_TBG_notype: "A2 without type features",
};
const POLICY: Record<string, string> = { none: "No auto-close", static: "A · Static", rolling: "B · Rolling", conformal: "C · Conformal-corrected" };
const TAB = "rounded-t px-3 py-2 text-sm font-medium text-slate-600 data-[state=active]:border-b-2 data-[state=active]:border-[#1E3A5F] data-[state=active]:text-[#1E3A5F] hover:text-slate-900";
const ci0 = (c: [number, number]) => c[0] > 0 || c[1] < 0;

export default function PerformancePage() {
  const { dataset } = useDataset();
  const state = useAsync(async () => ({ m: await getBackend().metrics(dataset), mode: getBackend().mode }), `metrics:${dataset}`);
  return (
    <>
      <PageHeader title="Model performance" subtitle="Observed experimental results on held-out days of synthetic data. Positives come from very few independent schemes, so every interval is wide — read effect sizes, not rankings." right={<div className="flex gap-2"><Badge tone="success">OBSERVED RESULTS</Badge><DataLabels demo={state.status === "success" && state.data.mode === "demo"} /></div>} />
      <Async state={state} label="Loading results">{({ m }) => <Body m={m} />}</Async>
    </>
  );
}

function Body({ m }: { m: Metrics }) {
  const c = m.h1.counts;
  return (
    <div className="space-y-4">
      <Notice tone="warn" title="Sample size:">
        Test window (new-scheme view): {fmtNum(c.test_strict_cases, 0)} cases, {c.test_strict_pos} positive cases from {c.test_strict_schemes} independent schemes. Validation calibration set: {c.val_cal_pos} positives. Run {m.run_id}.
      </Notice>
      <Tabs.Root defaultValue="ranking">
        <Tabs.List aria-label="Result sections" className="flex flex-wrap gap-1 border-b border-slate-200">
          {[["ranking", "Ranking (H1)"], ["calibration", "Calibration"], ["capacity", "Capacity"], ["ablations", "Ablations"], ["shift", "Family shift (H2)"], ["autoclose", "Auto-close (H3)"]].map(([v, l]) => (
            <Tabs.Trigger key={v} value={v} className={TAB}>{l}</Tabs.Trigger>
          ))}
        </Tabs.List>
        <div className="pt-4">
          <Tabs.Content value="ranking"><Ranking m={m} /></Tabs.Content>
          <Tabs.Content value="calibration"><Calibration m={m} /></Tabs.Content>
          <Tabs.Content value="capacity"><Capacity m={m} /></Tabs.Content>
          <Tabs.Content value="ablations"><Ablations m={m} /></Tabs.Content>
          <Tabs.Content value="shift"><Shift m={m} /></Tabs.Content>
          <Tabs.Content value="autoclose"><AutoClose m={m} /></Tabs.Content>
        </div>
      </Tabs.Root>
    </div>
  );
}

function ContrastTable({ rows }: { rows: Contrast[] }) {
  return (
    <TableWrap caption="Paired scheme-cluster bootstrap contrasts in recall at the review capacity">
      <thead><tr><Th>Comparison (A − B)</Th><Th className="text-right">Capacity m</Th><Th className="text-right">Recall A</Th><Th className="text-right">Recall B</Th><Th className="text-right">Difference</Th><Th className="text-right">95 % CI</Th><Th className="text-right">Schemes</Th></tr></thead>
      <tbody>
        {rows.map((r) => (
          <tr key={`${r.a}${r.b}${r.m}`} className={cn(r.primary && "bg-[#F3F7FB]")}>
            <Td>{SHORT[r.a]} − {SHORT[r.b]} {r.primary && <Badge tone="brand">primary H1</Badge>}</Td>
            <Td className="text-right">{r.m}×</Td><Td className="text-right">{fmtPct(r.recall)}</Td><Td className="text-right">{fmtPct(r.recall_b)}</Td>
            <Td className="text-right font-medium">{r.diff >= 0 ? "+" : "−"}{fmtFixed(Math.abs(r.diff) * 100, 1)} pp</Td>
            <Td className="text-right">{fmtFixed(r.diff_ci95[0] * 100, 1)} … {fmtFixed(r.diff_ci95[1] * 100, 1)} pp {ci0(r.diff_ci95) && <Badge tone="info">excludes 0</Badge>}</Td>
            <Td className="text-right">{r.n_clusters}</Td>
          </tr>
        ))}
      </tbody>
    </TableWrap>
  );
}

function Ranking({ m }: { m: Metrics }) {
  const [view, setView] = useState<"strict" | "all">("strict");
  const rows = ORDER.map((k) => ({ k, r: m.h1.models[k].test[view], n: m.h1.models[k].n_features }));
  const primary = m.h1.contrasts.find((c) => c.primary);
  return (
    <div className="space-y-4">
      <Card title="Models on the test block" subtitle="Mean ± sd over 3 seeds. Recall/precision at the daily review capacity K (m = 1 × training prevalence)" actions={
        <div role="group" aria-label="Evaluation view" className="flex overflow-hidden rounded border border-slate-300 text-xs">
          {(["strict", "all"] as const).map((v) => <button key={v} aria-pressed={view === v} onClick={() => setView(v)} className={cn("px-3 py-1", view === v ? "bg-[#1E3A5F] text-white" : "bg-white hover:bg-slate-50")}>{v === "strict" ? "New schemes only (primary)" : "All positives (incl. carry-over)"}</button>)}
        </div>}>
        <TableWrap caption="Model comparison">
          <thead><tr><Th>Model</Th><Th className="text-right">Features</Th><Th className="text-right">PR-AUC</Th><Th className="text-right">Recall@K (m=1)</Th><Th className="text-right">Precision@K</Th><Th className="text-right">Lift@K</Th></tr></thead>
          <tbody>
            {rows.map(({ k, r, n }) => {
              const t = r.topk["1.0"];
              return (
                <tr key={k}><Td>{SHORT[k]}</Td><Td className="text-right">{n}</Td>
                  <Td className="text-right">{fmtFixed(r.pr_auc.mean, 3)} ± {fmtFixed(r.pr_auc.sd, 3)}</Td>
                  <Td className="text-right">{fmtPct(t.recall.mean)} ± {fmtFixed(t.recall.sd * 100, 1)}</Td>
                  <Td className="text-right">{fmtPct(t.precision.mean)}</Td><Td className="text-right">{fmtNum(t.lift.mean, 0)}×</Td></tr>
              );
            })}
          </tbody>
        </TableWrap>
        <p className="mt-2 text-xs text-slate-500">{rows[0].r.n_pos} positive cases · {fmtNum(rows[0].r.n_cases, 0)} cases. {view === "all" ? "The all-positives view includes continuing schemes the model saw earlier — optimistic and favours memorising features." : "New-scheme view removes positives from schemes that started before the test block."}</p>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Precision–recall curve (M3, seed 1)" subtitle="New-scheme test view; prevalence is the baseline precision">
          <LineSeries data={m.h1.pr_curve_main} xKey="recall" xType="number" series={[{ key: "precision", label: "Precision", color: COLORS.blue }]} xFormat={(v) => fmtPct(Number(v), 0)} yFormat={(v) => fmtPct(v, 0)} ariaLabel="Precision-recall curve of the main model" />
        </Card>
        <Card title="H1 headline" subtitle="Does graph context add value over own-activity and behaviour features?">
          {primary && (
            <p className="text-sm text-slate-700">
              At the primary capacity the graph-enhanced model changes recall by <strong>{primary.diff >= 0 ? "+" : "−"}{fmtFixed(Math.abs(primary.diff) * 100, 1)} pp</strong> (95 % CI {fmtFixed(primary.diff_ci95[0] * 100, 1)} … {fmtFixed(primary.diff_ci95[1] * 100, 1)} pp, {primary.n_clusters} schemes).{" "}
              {ci0(primary.diff_ci95) ? "The interval excludes zero." : "The interval includes zero: no evidence that graph features improve prioritisation on this data."}
            </p>
          )}
        </Card>
      </div>
      <Card title="Paired contrasts" subtitle="Seed 1, resampling whole schemes (not cases)"><ContrastTable rows={m.h1.contrasts.filter((c) => c.m === 1 || c.m === 2)} /></Card>
    </div>
  );
}

function Calibration({ m }: { m: Metrics }) {
  const cal = m.h1.calibration["M3_lgbm_TBG"];
  const bins = [...cal.bins].sort((a, b) => a.mean_pred - b.mean_pred).map((b) => ({ mean_pred: b.mean_pred, obs: b.obs_rate, ideal: b.mean_pred }));
  return (
    <div className="space-y-4">
      <Card title="Reliability (M3, test, new-scheme view)" subtitle="Platt scaling fitted on validation only. Bins hold equal numbers of cases; most bins contain no positives at all, so points are noisy.">
        <LineSeries data={bins} xKey="mean_pred" xType="number" xFormat={(v) => fmtPct(Number(v), 2)} yFormat={(v) => fmtPct(v, 2)} ariaLabel="Reliability diagram: observed rate against mean predicted probability" series={[{ key: "obs", label: "Observed rate", color: COLORS.blue }, { key: "ideal", label: "Perfect calibration", color: COLORS.slate, dash: "5 4" }]} />
      </Card>
      <Card title="Calibration metrics by model" subtitle="At a prevalence below 0.1 %, ECE is small for almost any predictor; compare Brier with the prevalence-only baseline.">
        <TableWrap caption="Calibration metrics">
          <thead><tr><Th>Model</Th><Th className="text-right">Brier</Th><Th className="text-right">Baseline Brier</Th><Th className="text-right">Skill</Th><Th className="text-right">ECE</Th></tr></thead>
          <tbody>
            {ORDER.map((k) => { const c = m.h1.calibration[k]; return (
              <tr key={k}><Td>{SHORT[k]}</Td><Td className="text-right">{fmtFixed(c.brier * 1000, 3)}·10⁻³</Td><Td className="text-right">{fmtFixed(c.brier_baseline_prevalence * 1000, 3)}·10⁻³</Td>
                <Td className="text-right">{fmtPct(1 - c.brier / c.brier_baseline_prevalence, 1)}</Td><Td className="text-right">{fmtFixed(c.ece * 1000, 3)}·10⁻³</Td></tr>); })}
          </tbody>
        </TableWrap>
      </Card>
    </div>
  );
}

function Capacity({ m }: { m: Metrics }) {
  const ms = ["0.5", "1.0", "2.0", "5.0"];
  const data = ms.map((k) => ({ cap: `${Number(k)}×`, ...Object.fromEntries(ORDER.map((n) => [n, m.h1.models[n].test.strict.topk[k].recall.mean])) }));
  const colors = [COLORS.slate, COLORS.navy, COLORS.blue, COLORS.teal, COLORS.amber, COLORS.red];
  return (
    <div className="space-y-4">
      <Card title="Recall@K versus review capacity" subtitle="K per day = ceil(m × training prevalence × new cases). m = 1 is about as many reviews per day as expected positives in training.">
        <LineSeries data={data} xKey="cap" yFormat={(v) => fmtPct(v, 0)} ariaLabel="Recall at K against capacity multiplier for each model" series={ORDER.map((n, i) => ({ key: n, label: SHORT[n], color: colors[i] }))} yDomain={[0, 1]} />
      </Card>
      <Card title="Reviews per day">
        <TableWrap caption="Average reviews per day by capacity">
          <thead><tr><Th>Capacity m</Th><Th className="text-right">Reviews / day</Th>{ORDER.slice(1, 4).map((n) => <Th key={n} className="text-right">{SHORT[n].split(" ")[0]} precision</Th>)}</tr></thead>
          <tbody>{ms.map((k) => <tr key={k}><Td>{Number(k)}×</Td><Td className="text-right">{fmtNum(m.h1.models["M3_lgbm_TBG"].test.strict.topk[k].avg_k_per_day, 1)}</Td>{ORDER.slice(1, 4).map((n) => <Td key={n} className="text-right">{fmtPct(m.h1.models[n].test.strict.topk[k].precision.mean, 1)}</Td>)}</tr>)}</tbody>
        </TableWrap>
      </Card>
    </div>
  );
}

function Ablations({ m }: { m: Metrics }) {
  const data = ORDER.map((k) => ({ model: SHORT[k], "PR-AUC": m.h1.models[k].test.strict.pr_auc.mean, "Recall@K (m=1)": m.h1.models[k].test.strict.topk["1.0"].recall.mean }));
  const c = m.h1.contrasts.find((x) => x.a === "M3_lgbm_TBG" && x.b === "A2_lgbm_TBG_notype" && x.m === 1);
  return (
    <div className="space-y-4">
      <Card title="Feature-group ablations" subtitle="Same model class and hyper-parameters; only the feature set changes">
        <BarSeries data={data} xKey="model" layout="vertical" height={320} yFormat={(v) => fmtFixed(v, 2)} ariaLabel="Bar chart of PR-AUC and recall at K per model" series={[{ key: "PR-AUC", label: "PR-AUC", color: COLORS.blue }, { key: "Recall@K (m=1)", label: "Recall@K (m=1)", color: COLORS.teal }]} />
      </Card>
      {c && (
        <Notice tone="warn" title="Generator artefact:">
          Removing transaction-type features changes recall by {c.diff >= 0 ? "−" : "+"}{fmtFixed(Math.abs(c.diff) * 100, 1)} pp (M3 − A2: {c.diff >= 0 ? "+" : "−"}{fmtFixed(Math.abs(c.diff) * 100, 1)} pp, CI {fmtFixed(c.diff_ci95[0] * 100, 1)} … {fmtFixed(c.diff_ci95[1] * 100, 1)}). In this generator almost all fraud is of type <em>transfer</em>, so part of the measured signal is a property of the synthetic data, not evidence about real behaviour.
        </Notice>
      )}
      <Card title="Most important features (M3, gain)">
        <ul className="space-y-1 text-sm">{m.feature_importance_gain.slice(0, 10).map((f) => <li key={f.feature} className="flex items-center gap-2"><Badge tone="brand">{f.group}</Badge><span className="font-mono text-xs">{f.feature}</span><span className="text-slate-500">— {f.definition}</span></li>)}</ul>
      </Card>
    </div>
  );
}

function Shift({ m }: { m: Metrics }) {
  const fams = Object.values(m.h2.families);
  return (
    <div className="space-y-4">
      <Notice tone="info" title="Constructed distribution shift:">
        Each row retrains without one scheme family and measures recall on that family only (typology-family holdout). This is not natural concept drift. Window starts at day {m.h2.window_start_day}.
      </Notice>
      <Card title="Leave-one-family-out at m = 1" subtitle="Relative recall loss = (recall when family was seen − recall when held out) ÷ recall seen. Positive = worse when unseen.">
        <TableWrap caption="Family holdout results">
          <thead><tr><Th>Held-out family</Th><Th className="text-right">Schemes</Th><Th className="text-right">Positive cases</Th><Th className="text-right">M3 seen → held out</Th><Th className="text-right">M3 loss</Th><Th className="text-right">M4 seen → held out</Th><Th className="text-right">M4 loss</Th><Th className="text-right">M4 − M3 loss (95 % CI)</Th></tr></thead>
          <tbody>
            {fams.map((f) => { const b = f.by_m["1.0"]; const a3 = b["M3_lgbm_TBG"]; const a4 = b["M4_lgbm_TBGM"]; const d = b.diff_loss_M4_minus_M3; return (
              <tr key={f.family}>
                <Td>{f.family} {f.n_schemes < 5 && <Badge tone="warn" title="Fewer than 5 independent schemes">underpowered</Badge>}</Td>
                <Td className="text-right">{f.n_schemes}</Td><Td className="text-right">{f.n_pos_cases}</Td>
                <Td className="text-right">{fmtPct(a3.recall_seen.mean, 0)} → {fmtPct(a3.recall_heldout.mean, 0)}</Td><Td className="text-right">{fmtPct(a3.rel_loss.mean, 0)}</Td>
                <Td className="text-right">{fmtPct(a4.recall_seen.mean, 0)} → {fmtPct(a4.recall_heldout.mean, 0)}</Td><Td className="text-right">{fmtPct(a4.rel_loss.mean, 0)}</Td>
                <Td className="text-right">{d.point >= 0 ? "+" : "−"}{fmtFixed(Math.abs(d.point) * 100, 0)} pp ({fmtFixed(d.ci95[0] * 100, 0)} … {fmtFixed(d.ci95[1] * 100, 0)}) {ci0(d.ci95) && <Badge tone="info">excludes 0</Badge>}</Td>
              </tr>); })}
          </tbody>
        </TableWrap>
        <p className="mt-2 text-xs text-slate-500">Intervals resample schemes within the family. With one to a handful of schemes per family they cannot support a general claim; families with a single scheme have degenerate intervals.</p>
      </Card>
    </div>
  );
}

function AutoClose({ m }: { m: Metrics }) {
  const rows = m.h3.same_regime.filter((c) => c.m === 1);
  const alphas = [0.05, 0.1, 0.2];
  const chart = alphas.map((a) => ({ alpha: `α = ${fmtPct(a, 0)}`, Nominal: a, ...Object.fromEntries((["static", "rolling", "conformal"] as const).map((p) => [POLICY[p], rows.find((r) => r.policy === p && r.alpha === a)?.realised_miss_rate ?? null])) }));
  const base = m.h3.baseline_no_autoclose;
  const cell = (r: SimCell) => (
    <tr key={`${r.policy}${r.alpha}`}>
      <Td>{POLICY[r.policy]}</Td><Td className="text-right">{fmtPct(r.alpha, 0)}</Td>
      <Td className="text-right font-medium">{fmtPct(r.realised_miss_rate)} {r.miss_ci95 && r.miss_ci95[0] > r.alpha && <Badge tone="danger">above nominal</Badge>}</Td>
      <Td className="text-right">{fmtCI(r.miss_ci95)}</Td><Td className="text-right">{fmtPct(r.review_recall)}</Td><Td className="text-right">{fmtPct(r.expired_positive_rate)}</Td>
      <Td className="text-right">{fmtNum(r.mean_backlog, 0)}</Td><Td className="text-right">{r.violation_rate === null ? "n/a" : fmtPct(r.violation_rate, 0)}</Td>
    </tr>
  );
  const held: HeldoutCell[] = m.h3.heldout.filter((h) => h.policy.alpha === 0.1);
  return (
    <div className="space-y-4">
      <Notice tone="warn" title="How to read this:">
        Realised miss rate = positives in AUTO-CLOSE ÷ all positives; it is compared with the nominal tolerance α. Positives never reviewed also include those that <em>expire</em> in the backlog — a separate loss driven by capacity, not by the policy. No coverage guarantee is assumed: the conformal-corrected policy is measured, not trusted.
      </Notice>
      <Card title="Realised miss rate versus nominal tolerance (m = 1, same regime)"><BarSeries data={chart} xKey="alpha" yFormat={(v) => fmtPct(v, 0)} ariaLabel="Bar chart of realised miss rate by policy against nominal tolerance" series={[{ key: "Nominal", label: "Nominal α", color: "#CBD5E1" }, { key: POLICY.static, label: POLICY.static, color: COLORS.amber }, { key: POLICY.rolling, label: POLICY.rolling, color: COLORS.blue }, { key: POLICY.conformal, label: POLICY.conformal, color: COLORS.teal }]} /></Card>
      <Card title="Policies at m = 1" subtitle={`${m.h3.stream.n_pos} positives in the test stream. Baseline without auto-close: ${fmtPct(base["1.0"].review_recall)} reviewed, ${fmtPct(base["1.0"].expired_positive_rate)} expire, mean backlog ${fmtNum(base["1.0"].mean_backlog, 0)} cases.`}>
        <TableWrap caption="Auto-close policy results">
          <thead><tr><Th>Policy</Th><Th className="text-right">Nominal α</Th><Th className="text-right">Realised miss</Th><Th className="text-right">95 % CI</Th><Th className="text-right">Review recall</Th><Th className="text-right">Expired positives</Th><Th className="text-right">Mean backlog</Th><Th className="text-right">Weeks over α</Th></tr></thead>
          <tbody>{rows.map(cell)}</tbody>
        </TableWrap>
      </Card>
      <Card title="Held-out family (α = 10 %, m = 1)" subtitle="Model and calibration never saw the family; rolling and conformal policies receive delayed labels from the stream.">
        <TableWrap caption="Held-out family auto-close results">
          <thead><tr><Th>Held-out family</Th><Th>Policy</Th><Th className="text-right">Overall miss</Th><Th className="text-right">Held-out family miss</Th><Th className="text-right">Family positives</Th></tr></thead>
          <tbody>{held.map((h) => <tr key={h.heldout_family_name + h.policy.kind}><Td>{h.heldout_family_name}</Td><Td>{POLICY[h.policy.kind]}</Td><Td className="text-right">{fmtPct(h.realised_miss_rate)}</Td><Td className="text-right">{h.heldout_family_stats ? fmtPct(h.heldout_family_stats.miss) : "no positives"}</Td><Td className="text-right">{h.heldout_family_stats?.n_pos ?? 0}</Td></tr>)}</tbody>
        </TableWrap>
      </Card>
      <Card title="Selection-bias sensitivity" subtitle="Labels are only learned for cases an analyst reviewed (α = 10 %, m = 1)">
        <ul className="space-y-1 text-sm">{m.h3.review_only_labels.map((r) => <li key={r.policy.kind}>{POLICY[r.policy.kind]}: realised miss {fmtPct(r.realised_miss_rate)} (95 % CI {fmtCI(r.miss_ci95)}) against nominal 10 %.</li>)}</ul>
      </Card>
    </div>
  );
}
