"use client";
import * as Switch from "@radix-ui/react-switch";
import { useState } from "react";
import { Async, Badge, Card, DataLabels, Notice, PageHeader, Stat, cn } from "@/components/ui";
import { getBackend, setMode } from "@/lib/api";
import { LIVE_AVAILABLE } from "@/lib/config";
import { fmtCI, fmtNum, fmtPct } from "@/lib/format";
import { useAsync, useDataset } from "@/lib/hooks";
import type { PolicyKind } from "@/lib/types";

const POLICIES: { v: PolicyKind; label: string; help: string }[] = [
  { v: "none", label: "No auto-close", help: "Only the review queue; nothing is closed automatically." },
  { v: "static", label: "A · Static threshold", help: "Threshold fixed on validation positives." },
  { v: "rolling", label: "B · Rolling recalibration", help: "Re-estimated from delayed labels (3-day delay)." },
  { v: "conformal", label: "C · Conformal-corrected", help: "Finite-sample corrected, sliding 60-day window. Not a guarantee." },
];
const ALPHAS = [0.05, 0.1, 0.2];
const CAPS = [0.5, 1, 2, 5];

function Choice<T extends string | number>({ legend, value, options, onChange, fmt }: { legend: string; value: T; options: T[]; onChange: (v: T) => void; fmt: (v: T) => string }) {
  return (
    <fieldset className="mb-4">
      <legend className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button key={String(o)} type="button" aria-pressed={value === o} onClick={() => onChange(o)} className={cn("rounded border px-3 py-1.5 text-sm", value === o ? "border-[#1E3A5F] bg-[#1E3A5F] text-white" : "border-slate-300 bg-white hover:bg-slate-50")}>
            {fmt(o)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function SettingsPage() {
  const { dataset } = useDataset();
  const [policy, setPolicy] = useState<PolicyKind>("static");
  const [alpha, setAlpha] = useState(0.1);
  const [cap, setCap] = useState(1);
  const sim = useAsync(async () => {
    const b = getBackend();
    const [res, dash] = await Promise.all([b.simulate({ dataset, policy, alpha, capacity_multiplier: cap }), b.dashboard(dataset)]);
    return { res, perDay: dash.summary.primary.avg_review_per_day / dash.summary.primary.capacity_multiplier };
  }, `sim:${dataset}:${policy}:${alpha}:${cap}`);
  const health = useAsync(() => getBackend().health(), "health");
  const mode = getBackend().mode;
  return (
    <>
      <PageHeader title="Settings" subtitle="Change the review capacity, the auto-close tolerance and the calibration policy, and see what the recorded experiment says would have happened on the held-out days." right={<DataLabels demo={mode === "demo"} />} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Configuration">
          <Choice legend="Review capacity (× training prevalence)" value={cap} options={CAPS} onChange={setCap} fmt={(v) => `${v}×`} />
          <Choice legend="Auto-close policy / calibration" value={policy} options={POLICIES.map((p) => p.v)} onChange={setPolicy} fmt={(v) => POLICIES.find((p) => p.v === v)!.label} />
          <p className="-mt-2 mb-4 text-xs text-slate-500">{POLICIES.find((p) => p.v === policy)!.help}</p>
          <div className={policy === "none" ? "opacity-40" : undefined}>
            <Choice legend="Auto-close tolerance α (target share of positives auto-closed)" value={alpha} options={ALPHAS} onChange={setAlpha} fmt={(v) => fmtPct(v, 0)} />
          </div>
          {mode === "demo" && <Notice tone="info">Demo mode shows precomputed grid results from the recorded run. With a connected API any value can be simulated.</Notice>}
        </Card>
        <Card title="What this setting would have done" subtitle={`${dataset} condition · new-scheme test stream`}>
          <Async state={sim} label="Computing result">
            {({ res, perDay }) => (
              <div className="space-y-3" aria-live="polite">
                <p className="text-sm text-slate-800" data-testid="plain-summary">
                  At <strong>{cap}×</strong> capacity (about <strong>{fmtNum(perDay * cap, 1)} reviews per day</strong>){res.policy === "none" ? ", with no auto-close" : <>, policy <strong>{POLICIES.find((p) => p.v === res.policy)!.label}</strong> at α = {fmtPct(res.alpha, 0)}</>}: <strong>{fmtPct(res.review_recall)}</strong> of positive cases are reviewed
                  {res.policy !== "none" && <>, <strong>{fmtPct(res.realised_miss_rate)}</strong> are auto-closed (95 % CI {fmtCI(res.miss_ci95)})</>}, and <strong>{fmtPct(res.expired_positive_rate)}</strong> expire unreviewed in the backlog.
                </p>
                <dl className="grid grid-cols-2 gap-3">
                  <Stat label="Positives reviewed" value={fmtPct(res.review_recall)} />
                  <Stat label="Auto-closed positives" value={res.policy === "none" ? "—" : fmtPct(res.realised_miss_rate)} tone={res.policy !== "none" && res.miss_ci95 && res.miss_ci95[0] > res.alpha ? "danger" : undefined} hint={res.policy === "none" ? undefined : `nominal ${fmtPct(res.alpha, 0)}`} />
                  <Stat label="Backlog (mean / max)" value={`${fmtNum(res.mean_backlog, 0)} / ${fmtNum(res.max_backlog, 0)}`} />
                  <Stat label="Cases auto-closed" value={fmtPct(res.workload_removed, 1)} hint={`${fmtNum(res.auto_closed_cases, 0)} cases`} />
                </dl>
                {res.note && <p className="text-xs text-slate-500">{res.note}</p>}
              </div>
            )}
          </Async>
        </Card>
        <Card title="API status">
          <Async state={health} label="Checking API">
            {(h) => (
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                <dt className="text-slate-500">Mode</dt><dd><Badge tone={mode === "demo" ? "info" : "success"}>{mode === "demo" ? "DEMO (static bundle)" : "LIVE API"}</Badge></dd>
                <dt className="text-slate-500">Status</dt><dd>{h.status === "ok" ? "Healthy" : "Degraded"}</dd>
                <dt className="text-slate-500">Version</dt><dd>{h.version}</dd>
                <dt className="text-slate-500">Model loaded</dt><dd>{h.model_loaded ? "Yes" : mode === "demo" ? "Not needed in demo" : "No"}</dd>
              </dl>
            )}
          </Async>
        </Card>
        <Card title="Demo / live mode">
          {LIVE_AVAILABLE ? (
            <label className="flex items-center gap-3 text-sm">
              <Switch.Root checked={mode === "live"} onCheckedChange={(on) => { setMode(on ? "live" : "demo"); window.location.reload(); }} aria-label="Use live API" className="relative h-5 w-9 rounded-full bg-slate-300 data-[state=checked]:bg-[#1E3A5F]">
                <Switch.Thumb className="block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-4" />
              </Switch.Root>
              Use live API ({mode === "live" ? "on" : "off"})
            </label>
          ) : (
            <p className="text-sm text-slate-600">No API URL is configured for this build (<code className="rounded bg-slate-100 px-1">NEXT_PUBLIC_API_URL</code>), so the app runs in demo mode with a static bundle of recorded results.</p>
          )}
        </Card>
      </div>
    </>
  );
}
