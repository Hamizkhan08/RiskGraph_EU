"use client";
import * as Slider from "@radix-ui/react-slider";
import * as Switch from "@radix-ui/react-switch";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { NetworkDetails, NetworkGraph, NetworkLegend, type Selection } from "@/components/NetworkGraph";
import { Async, Card, DataLabels, EmptyState, Loading, PageHeader, Td, TableWrap, Th } from "@/components/ui";
import { getBackend } from "@/lib/api";
import { fmtDateTime, fmtNum } from "@/lib/format";
import { useAsync, useDataset } from "@/lib/hooks";
import type { CaseDetail } from "@/lib/types";

export default function NetworkPage() {
  return (
    <Suspense fallback={<Loading label="Loading network view" />}>
      <NetworkInner />
    </Suspense>
  );
}

function NetworkInner() {
  const { dataset } = useDataset();
  const sp = useSearchParams();
  const [picked, setPicked] = useState<string | null>(null);
  const list = useAsync(async () => (await getBackend().alerts({ dataset, q: "", priority: "", status: "", sort: "score", order: "desc", page: 1, pageSize: 50 })).items, `netlist:${dataset}`);
  const fromUrl = sp.get("case");
  return (
    <>
      <PageHeader title="Network analysis" subtitle="Ego network of the focal account over the 7 days before the decision timestamp — built only from transactions available at that moment." right={<DataLabels demo={getBackend().mode === "demo"} />} />
      <Async state={list} label="Loading cases">
        {(items) => {
          if (items.length === 0) return <Card><EmptyState title="No cases available" body="There are no alerts for this dataset." /></Card>;
          const id = picked ?? fromUrl ?? items[0].id;
          return (
            <div className="space-y-4">
              <Card>
                <label className="flex flex-wrap items-center gap-3 text-sm font-medium text-slate-700">
                  Case
                  <select value={id} onChange={(e) => setPicked(e.target.value)} className="rounded border border-slate-300 bg-white px-2 py-1.5 font-mono text-xs">
                    {!items.some((i) => i.id === id) && <option value={id}>{id}</option>}
                    {items.map((i) => <option key={i.id} value={i.id}>{i.id}</option>)}
                  </select>
                  <Link href={`/alerts/${id}`} className="text-[#1E3A5F] hover:underline">Open case →</Link>
                </label>
              </Card>
              <CaseNetwork id={id} />
            </div>
          );
        }}
      </Async>
    </>
  );
}

function CaseNetwork({ id }: { id: string }) {
  const state = useAsync(() => getBackend().caseDetail(id), `netcase:${id}`);
  return <Async state={state} label="Loading network">{(c) => <Explorer key={c.id} c={c} />}</Async>;
}

function Explorer({ c }: { c: CaseDetail }) {
  const ev = c.evidence;
  const maxAmt = Math.max(1, ...ev.edges.map((e) => e.amount));
  const [labels, setLabels] = useState(true);
  const [min, setMin] = useState(0);
  const [sel, setSel] = useState<Selection>(null);
  if (ev.edges.length === 0) return <Card><EmptyState title="No flows in the window" body="This account has no account-to-account flows among the shown counterparties." /></Card>;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2" title={`Focal account ${ev.focal}`} subtitle={`Showing ${ev.nodes.length - 1} of ${fmtNum(ev.counterparties_total, 0)} counterparties (largest by amount) · decision timestamp ${fmtDateTime(ev.decision_timestamp)} UTC`}>
        <div className="mb-3 flex flex-wrap items-center gap-6 text-sm">
          <label className="flex items-center gap-2">
            <Switch.Root checked={labels} onCheckedChange={setLabels} aria-label="Show node labels" className="relative h-5 w-9 rounded-full bg-slate-300 data-[state=checked]:bg-[#1E3A5F]">
              <Switch.Thumb className="block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-4" />
            </Switch.Root>
            Labels
          </label>
          <label className="flex items-center gap-2">
            <span id="min-amt">Minimum flow amount: <strong className="tabular-nums">{fmtNum(min, 0)}</strong></span>
            <Slider.Root value={[min]} min={0} max={Math.ceil(maxAmt)} step={Math.max(1, Math.round(maxAmt / 50))} onValueChange={(v) => setMin(v[0])} className="relative flex h-5 w-40 touch-none select-none items-center">
              <Slider.Track className="relative h-1.5 grow rounded-full bg-slate-200"><Slider.Range className="absolute h-full rounded-full bg-[#3B6EA8]" /></Slider.Track>
              <Slider.Thumb aria-labelledby="min-amt" className="block h-4 w-4 rounded-full border border-slate-400 bg-white shadow" />
            </Slider.Root>
          </label>
          <button onClick={() => { setMin(0); setLabels(true); setSel(null); }} className="rounded border border-slate-300 px-3 py-1 hover:bg-slate-50">Reset view</button>
        </div>
        <NetworkGraph nodes={ev.nodes} edges={ev.edges} height={460} showLabels={labels} minAmount={min} selected={sel} onSelect={setSel} />
        <div className="mt-3"><NetworkLegend /></div>
      </Card>
      <div className="space-y-4">
        <Card title="Selection"><NetworkDetails selection={sel} nodes={ev.nodes} edges={ev.edges} /></Card>
        <Card title="Flows (table view)">
          <details>
            <summary className="cursor-pointer text-sm font-medium text-[#1E3A5F]">Show all {ev.edges.length} flows</summary>
            <div className="mt-2">
              <TableWrap caption="Flows between shown accounts">
                <thead><tr><Th>From</Th><Th>To</Th><Th className="text-right">Tx</Th><Th className="text-right">Amount</Th></tr></thead>
                <tbody>{ev.edges.map((e) => <tr key={`${e.source}${e.target}`}><Td className="font-mono text-xs">{e.source}</Td><Td className="font-mono text-xs">{e.target}</Td><Td className="text-right">{e.n}</Td><Td className="text-right">{fmtNum(e.amount, 0)}</Td></tr>)}</tbody>
              </TableWrap>
            </div>
          </details>
        </Card>
      </div>
    </div>
  );
}
