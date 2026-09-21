"use client";
import { Async, Badge, Card, DataLabels, Notice, PageHeader, Td, TableWrap, Th } from "@/components/ui";
import { getBackend } from "@/lib/api";
import { DISCLOSURE } from "@/lib/config";
import { fmtCI, fmtDate, fmtFixed, fmtNum, fmtPct } from "@/lib/format";
import { useAsync, useDataset } from "@/lib/hooks";
import type { DataQuality, Metrics, Summary } from "@/lib/types";

export default function ResearchPage() {
  const { dataset } = useDataset();
  const state = useAsync(async () => {
    const b = getBackend();
    const [m, d, dq] = await Promise.all([b.metrics(dataset), b.dashboard(dataset), b.dataQuality(dataset)]);
    return { m, s: d.summary, dq, mode: b.mode };
  }, `research:${dataset}`);
  return (
    <>
      <PageHeader title="Research" subtitle="Question, hypotheses, method, data, validation design, findings and limitations of this prototype." right={<DataLabels demo={state.status === "success" && state.data.mode === "demo"} />} />
      <Async state={state} label="Loading research summary">{({ m, s, dq }) => <View m={m} s={s} dq={dq} />}</Async>
    </>
  );
}

function View({ m, s, dq }: { m: Metrics; s: Summary; dq: DataQuality }) {
  const primary = m.h1.contrasts.find((c) => c.primary);
  const fams = Object.values(m.h2.families);
  const better = fams.filter((f) => f.by_m["1.0"].diff_loss_M4_minus_M3.point < 0).length;
  const clear = fams.filter((f) => f.by_m["1.0"].diff_loss_M4_minus_M3.ci95[1] < 0 || f.by_m["1.0"].diff_loss_M4_minus_M3.ci95[0] > 0).length;
  const sch = fams.map((f) => f.n_schemes);
  const g = (p: string) => m.h3.same_regime.find((c) => c.policy === p && c.alpha === 0.1 && c.m === 1)!;
  const a2 = m.h1.contrasts.find((c) => c.a === "M3_lgbm_TBG" && c.b === "A2_lgbm_TBG_notype" && c.m === 1);
  const base = m.h3.baseline_no_autoclose["1.0"];
  const pct = (v: number) => `${v >= 0 ? "+" : "−"}${fmtFixed(Math.abs(v) * 100, 1)} pp`;
  return (
    <div className="space-y-4">
      <Card title="Research question">
        <p className="text-sm text-slate-800">Under a fixed daily review capacity, how reliably can transaction, behavioural and graph-based signals prioritise suspicious cases over time — and how does the reliability of calibrated auto-closure change under temporal, prevalence and unseen-typology-family shift?</p>
        <p className="mt-2 text-xs text-slate-500">Constructed shifts only (temporal split, LI/HI prevalence conditions, structural-family holdout). Nothing here claims to measure real-world AML effectiveness.</p>
      </Card>
      <Card title="Hypotheses and observed outcome" subtitle="Outcomes are computed from the recorded run and shown for the selected condition">
        <TableWrap caption="Hypotheses">
          <thead><tr><Th>Hypothesis</Th><Th>Observed on this condition</Th></tr></thead>
          <tbody>
            <tr><Td><strong>H1</strong> Behavioural + graph context improves recall@K over own-activity + behaviour features at fixed capacity.</Td>
              <Td>{primary ? <>Recall difference {pct(primary.diff)} (95 % CI {fmtFixed(primary.diff_ci95[0] * 100, 1)} … {fmtFixed(primary.diff_ci95[1] * 100, 1)} pp; {primary.n_clusters} schemes). {primary.diff_ci95[0] > 0 ? <Badge tone="success">supported</Badge> : primary.diff_ci95[1] < 0 ? <Badge tone="danger">contradicted</Badge> : <Badge tone="warn">not supported — inconclusive</Badge>}</> : "n/a"}</Td></tr>
            <tr><Td><strong>H2</strong> Typology-aware (motif) features lose less recall than generic features when a scheme family is held out.</Td>
              <Td>Motif model loses less in {better} of {fams.length} families, but the interval excludes zero in {clear}. Schemes per family: {Math.min(...sch)}–{Math.max(...sch)}. {clear === 0 ? <Badge tone="warn">inconclusive</Badge> : <Badge tone="warn">weak, underpowered</Badge>}</Td></tr>
            <tr><Td><strong>H3</strong> Auto-close realised miss rate stays near its nominal tolerance; recalibration and conformal correction reduce violations under shift. No guarantee is assumed.</Td>
              <Td>At α = 10 %: static {fmtPct(g("static").realised_miss_rate)} ({fmtCI(g("static").miss_ci95)}), rolling {fmtPct(g("rolling").realised_miss_rate)} ({fmtCI(g("rolling").miss_ci95)}), conformal-corrected {fmtPct(g("conformal").realised_miss_rate)} ({fmtCI(g("conformal").miss_ci95)}). {g("static").miss_ci95 && g("static").miss_ci95![0] > 0.1 ? <Badge tone="danger">static violates nominal</Badge> : <Badge tone="warn">static not clearly above nominal</Badge>}</Td></tr>
          </tbody>
        </TableWrap>
      </Card>
      <Card title="Findings (this condition)">
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-800">
          <li>Capacity dominates: at the primary capacity only {fmtPct(g("static").review_recall)} of positive cases are reviewed. With no auto-close, {fmtPct(base.expired_positive_rate)} of positives expire in a backlog averaging {fmtNum(base.mean_backlog, 0)} cases; auto-close mostly redistributes the unreviewed cases rather than finding more positives.</li>
          {a2 && <li>A large share of the signal comes from transaction type, a generator artefact: removing type features changes recall by {pct(-a2.diff)} (CI {fmtFixed(-a2.diff_ci95[1] * 100, 1)} … {fmtFixed(-a2.diff_ci95[0] * 100, 1)} pp).</li>}
          <li>Calibration skill is modest: Brier {fmtPct(1 - m.h1.calibration["M3_lgbm_TBG"].brier / m.h1.calibration["M3_lgbm_TBG"].brier_baseline_prevalence, 1)} better than a prevalence-only predictor.</li>
          <li>If labels arrive only for reviewed cases, the conformal-corrected policy misses {fmtPct(m.h3.review_only_labels.find((r) => r.policy.kind === "conformal")?.realised_miss_rate ?? NaN)} against a 10 % target — selection bias breaks the calibration assumption.</li>
        </ul>
      </Card>
      <Card title="Method">
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-800">
          <li><strong>Unit and timestamp:</strong> case = (account, day); the decision timestamp is the end of the day — features use only earlier or same-day transactions (automated future-perturbation test).</li>
          <li><strong>Feature groups:</strong> T own activity · B behavioural history · G generic graph context (7-day window graph) · M typology/motif-aware (cycles, bursts, pass-through, near-threshold amounts). Labels, scheme and family fields are never features.</li>
          <li><strong>Models:</strong> logistic regression (T+B), gradient boosting (T+B), graph-enhanced boosting (T+B+G), motif-aware boosting (T+B+G+M), two ablations. Fixed hyper-parameters, no tuning, three seeds. No GNN: not justified by the evidence or compute.</li>
          <li><strong>Split:</strong> burn-in {fmtDate(s.split.burn_in.dates[0])}–{fmtDate(s.split.burn_in.dates[1])} · train {fmtDate(s.split.train.dates[0])}–{fmtDate(s.split.train.dates[1])} · validation {fmtDate(s.split.validation.dates[0])}–{fmtDate(s.split.validation.dates[1])} · purge · test {fmtDate(s.split.test.dates[0])}–{fmtDate(s.split.test.dates[1])}. Scheme-start rule: positives from schemes that began before a block are excluded from its primary evaluation (schemes are long-lived).</li>
          <li><strong>Capacity:</strong> K per day = ceil(m × training prevalence × new cases). <strong>Zones:</strong> REVIEW, AUTO-CLOSE, BACKLOG (expires after 3 days), mutually exclusive.</li>
          <li><strong>Uncertainty:</strong> bootstrap resampling of whole laundering schemes (500 resamples), paired for model contrasts.</li>
        </ul>
      </Card>
      <Card title="Datasets" subtitle="What was and was not used">
        <TableWrap caption="Datasets">
          <thead><tr><Th>Dataset</Th><Th>Role</Th><Th>Licence / status</Th></tr></thead>
          <tbody>
            <tr><Td>Tide generator, LI-like &amp; HI-like (this build)</Td><Td>Primary. Generated locally, 1,500 individuals, 12 months, same population, {fmtPct(dq.positive_prevalence_tx, 3)} transaction-level illicit ratio for {s.dataset}.</Td><Td>Generator MIT. <strong>Not the published Zenodo release</strong>; that record&apos;s licence was not verified.</Td></tr>
            <tr><Td>AMLNet v2.0</Td><Td>Not used.</Td><Td>CC BY-NC 4.0 (verified from the record). Typologies are stages, not families; no scheme IDs; a model-generated score column. Adapter is untested on the real file.</Td></tr>
            <tr><Td>TransXion</Td><Td>Not used.</Td><Td>Data licence not verified.</Td></tr>
            <tr><Td>IBM AML (AMLworld)</Td><Td>Legacy profiling only; not used in results.</Td><Td>CDLA-Sharing-1.0.</Td></tr>
          </tbody>
        </TableWrap>
      </Card>
      <Card title="Limitations">
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-800">
          <li>Synthetic data from one generator at reduced scale; results do not transfer to real institutions, and nothing here measures real-world effectiveness.</li>
          <li>Very few independent schemes in the test period ({m.h1.counts.test_strict_schemes}), so intervals are wide and every ranking of models is fragile. H2 is underpowered.</li>
          <li>Transaction type is a near-giveaway in the generator; node attributes that would leak the target were excluded.</li>
          <li>LI and HI share one base population and differ only in injection; they are not independent datasets.</li>
          <li>Amounts have no currency conversion in the source, so aggregate amounts are nominal.</li>
          <li>Analyst decisions in demo mode are simulated feedback and change nothing about the model.</li>
        </ul>
      </Card>
      <Notice tone="warn" title="Responsible use:">{DISCLOSURE} An alert or elevated score is a prioritisation signal, never a finding that an offence occurred.</Notice>
    </div>
  );
}
