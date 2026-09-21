"use client";
import { useState } from "react";
import { AlertsTable } from "@/components/AlertsTable";
import { Async, Card, DataLabels, EmptyState, PageHeader } from "@/components/ui";
import { getBackend } from "@/lib/api";
import { fmtNum } from "@/lib/format";
import { useAsync, useDataset } from "@/lib/hooks";
import type { AlertQuery } from "@/lib/types";

const SELECT = "rounded border border-slate-300 bg-white px-2 py-1.5 text-sm";

export default function AlertsPage() {
  const { dataset } = useDataset();
  const [f, setF] = useState<Omit<AlertQuery, "dataset">>({ q: "", priority: "", status: "", sort: "date", order: "desc", page: 1, pageSize: 25 });
  const query: AlertQuery = { dataset, ...f };
  const update = (p: Partial<typeof f>) => setF((old) => ({ ...old, page: 1, ...p }));
  const state = useAsync(async () => ({ page: await getBackend().alerts(query), mode: getBackend().mode }), `alerts:${JSON.stringify(query)}`);
  const filtered = f.q !== "" || f.priority !== "" || f.status !== "";
  return (
    <>
      <PageHeader title="Alerts" subtitle="Cases entering the analyst REVIEW queue. Priority: P1 = top 10 % by score in the sampled queue, P2 = next 30 %, P3 = rest." right={<DataLabels demo={state.status === "success" && state.data.mode === "demo"} />} />
      <Card>
        <form role="search" aria-label="Filter alerts" className="mb-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <label className="flex flex-col text-xs font-medium text-slate-600">
            Search
            <input type="search" value={f.q} maxLength={64} onChange={(e) => update({ q: e.target.value })} placeholder="Case ID, account, reason" className={`${SELECT} w-56`} />
          </label>
          <label className="flex flex-col text-xs font-medium text-slate-600">
            Priority
            <select value={f.priority} onChange={(e) => update({ priority: e.target.value as AlertQuery["priority"] })} className={SELECT}>
              <option value="">All</option><option value="P1">Priority 1</option><option value="P2">Priority 2</option><option value="P3">Priority 3</option>
            </select>
          </label>
          <label className="flex flex-col text-xs font-medium text-slate-600">
            Status
            <select value={f.status} onChange={(e) => update({ status: e.target.value as AlertQuery["status"] })} className={SELECT}>
              <option value="">All</option><option value="open">Open</option><option value="suspicious">Suspicious</option><option value="false_positive">False positive</option><option value="requires_review">Requires review</option>
            </select>
          </label>
          <label className="flex flex-col text-xs font-medium text-slate-600">
            Sort by
            <select value={f.sort} onChange={(e) => update({ sort: e.target.value as AlertQuery["sort"] })} className={SELECT}>
              <option value="date">Date</option><option value="score">Risk score</option><option value="priority">Priority</option><option value="amount">Amount (7 days)</option>
            </select>
          </label>
          <button type="button" onClick={() => update({ order: f.order === "desc" ? "asc" : "desc" })} className={`${SELECT} font-medium`} aria-label={`Sort order: ${f.order === "desc" ? "descending" : "ascending"}. Activate to reverse.`}>
            {f.order === "desc" ? "↓ Descending" : "↑ Ascending"}
          </button>
          <label className="flex flex-col text-xs font-medium text-slate-600">
            Per page
            <select value={f.pageSize} onChange={(e) => update({ pageSize: Number(e.target.value) })} className={SELECT}>
              <option value={10}>10</option><option value={25}>25</option><option value={50}>50</option>
            </select>
          </label>
        </form>
        <Async state={state} label="Loading alerts">
          {({ page }) => {
            if (page.total === 0) {
              return filtered ? (
                <EmptyState kind="no-results" title="No alerts match these filters" body="Try a different search term or clear the filters." action={<button onClick={() => update({ q: "", priority: "", status: "" })} className="rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-50">Clear filters</button>} />
              ) : (
                <EmptyState title="No alerts in this dataset" body="The queue for this condition is empty." />
              );
            }
            const last = Math.max(1, Math.ceil(page.total / page.page_size));
            const lo = (page.page - 1) * page.page_size + 1;
            return (
              <div className="space-y-3">
                <AlertsTable items={page.items} caption="Alert queue" />
                <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600">
                  <p aria-live="polite">Showing {fmtNum(lo, 0)}–{fmtNum(lo + page.items.length - 1, 0)} of {fmtNum(page.total, 0)} alerts</p>
                  <div className="flex items-center gap-2">
                    <button disabled={page.page <= 1} onClick={() => setF((o) => ({ ...o, page: o.page - 1 }))} className="rounded border border-slate-300 px-3 py-1 enabled:hover:bg-slate-50 disabled:opacity-40">Previous</button>
                    <span>Page {page.page} of {last}</span>
                    <button disabled={page.page >= last} onClick={() => setF((o) => ({ ...o, page: o.page + 1 }))} className="rounded border border-slate-300 px-3 py-1 enabled:hover:bg-slate-50 disabled:opacity-40">Next</button>
                  </div>
                </nav>
              </div>
            );
          }}
        </Async>
      </Card>
    </>
  );
}
