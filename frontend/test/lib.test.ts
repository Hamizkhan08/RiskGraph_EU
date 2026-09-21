import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, createDemoBackend, createLiveBackend, queryAlerts } from "@/lib/api";
import { fmtCI, fmtDate, fmtDateTime, fmtMoney, fmtNum, fmtPct, parseTs } from "@/lib/format";
import type { Alert, AlertQuery } from "@/lib/types";
import { fixtureAlerts, installFetch } from "./helpers";

const Q: AlertQuery = { dataset: "LI", q: "", priority: "", status: "", sort: "date", order: "desc", page: 1, pageSize: 5 };
const norm = (s: string) => s.replace(/[\u00a0\u202f]/g, " ");

describe("European formatting", () => {
  it("formats numbers, percentages and currency the German/European way", () => {
    expect(fmtNum(1234567.891, 2)).toBe("1.234.567,89");
    expect(norm(fmtPct(0.1234, 1))).toBe("12,3 %");
    expect(norm(fmtMoney(1234.5, "EUR"))).toBe("1.234,50 €");
    expect(norm(fmtMoney(10, "GBP"))).toContain("£");
    expect(fmtMoney(10, "NOT-A-CCY")).toBe("10,00 NOT-A-CCY");
  });
  it("formats dates dd/mm/yyyy with 24 h UTC times and parses pandas-style timestamps", () => {
    expect(fmtDate("2025-10-12")).toBe("12/10/2025");
    expect(fmtDateTime("2025-10-12T09:05:00")).toBe("12/10/2025, 09:05");
    expect(fmtDateTime("2025-10-13 00:00:00")).toBe("13/10/2025, 00:00");
    expect(parseTs("2025-10-13 00:00:00").toISOString()).toBe("2025-10-13T00:00:00.000Z");
  });
  it("formats intervals and missing intervals", () => {
    expect(norm(fmtCI([0.04, 0.223]))).toBe("4,0 % – 22,3 %");
    expect(fmtCI(null)).toBe("n/a");
  });
});

describe("queryAlerts (mirrors the API semantics)", () => {
  const all = fixtureAlerts() as unknown as Alert[];
  it("paginates, sorts and filters", () => {
    const p1 = queryAlerts(all, Q);
    expect(p1.total).toBe(all.length);
    expect(p1.items).toHaveLength(5);
    const byScore = queryAlerts(all, { ...Q, sort: "score", pageSize: 50 }).items.map((a) => a.score);
    expect(byScore).toEqual([...byScore].sort((a, b) => b - a));
    const asc = queryAlerts(all, { ...Q, sort: "score", order: "asc", pageSize: 50 }).items.map((a) => a.score);
    expect(asc).toEqual([...asc].sort((a, b) => a - b));
    const p1only = queryAlerts(all, { ...Q, priority: "P1", pageSize: 50 });
    expect(p1only.items.every((a) => a.priority === "P1")).toBe(true);
    expect(queryAlerts(all, { ...Q, q: "zzzz-nothing" }).total).toBe(0);
    expect(queryAlerts(all, { ...Q, page: 99 }).items).toHaveLength(0);
    expect(queryAlerts(all, { ...Q, q: all[0].id.toUpperCase() }).total).toBe(1);
  });
});

describe("demo backend", () => {
  beforeEach(() => void installFetch());
  it("serves the bundle and persists simulated decisions locally", async () => {
    const b = createDemoBackend();
    const page = await b.alerts({ ...Q, pageSize: 50 });
    const id = page.items[0].id;
    expect((await b.caseDetail(id)).status).toBe("open");
    const rec = await b.decide(id, { decision: "suspicious", note: "n", analyst: "t" });
    expect(rec.simulated).toBe(true);
    await b.decide(id, { decision: "false_positive", note: "", analyst: "t" });
    const c = await b.caseDetail(id);
    expect(c.status).toBe("false_positive");
    expect(c.decision_history).toHaveLength(2);
    expect((await b.alerts({ ...Q, status: "false_positive", pageSize: 50 })).total).toBe(1);
    const dash = await b.dashboard("LI");
    expect(dash.decisions.decided_in_sample).toBe(1);
  });
  it("rejects malformed and unknown case ids", async () => {
    const b = createDemoBackend();
    await expect(b.caseDetail("../../etc/passwd")).rejects.toMatchObject({ status: 422 });
    await expect(b.caseDetail("RG-LI-1-20250101")).rejects.toMatchObject({ status: 404 });
    await expect(b.caseDetail("RG-HI-1-20250101")).rejects.toBeInstanceOf(ApiError);
  });
  it("answers settings from the precomputed grid and rejects off-grid settings", async () => {
    const b = createDemoBackend();
    const r = await b.simulate({ dataset: "LI", policy: "static", alpha: 0.1, capacity_multiplier: 1 });
    expect(r.realised_miss_rate).toBeGreaterThan(0);
    const none = await b.simulate({ dataset: "LI", policy: "none", alpha: 0.1, capacity_multiplier: 2 });
    expect(none.auto_closed_cases).toBe(0);
    await expect(b.simulate({ dataset: "LI", policy: "static", alpha: 0.33, capacity_multiplier: 1 })).rejects.toMatchObject({ status: 404 });
  });
});

describe("live backend", () => {
  it("builds query strings, posts JSON and maps API errors", async () => {
    const fn = vi.fn(async (u: RequestInfo | URL) => {
      if (String(u).includes("/decision")) return { ok: false, status: 422, json: async () => ({ detail: "bad note" }) } as Response;
      return { ok: true, status: 200, json: async () => ({ items: [], total: 0, page: 1, page_size: 5 }) } as Response;
    });
    vi.stubGlobal("fetch", fn);
    const b = createLiveBackend("https://api.example");
    await b.alerts({ ...Q, q: "a b", priority: "P1" });
    const url = String(fn.mock.calls[0][0]);
    expect(url).toContain("https://api.example/api/alerts?");
    expect(url).toContain("q=a+b");
    expect(url).toContain("priority=P1");
    expect(url).toContain("page_size=5");
    await expect(b.decide("RG-LI-1-20250101", { decision: "suspicious", note: "", analyst: "x" })).rejects.toMatchObject({ status: 422, message: "bad note" });
    expect((fn.mock.calls[1] as unknown[])[1]).toMatchObject({ method: "POST" });
  });
});
