import { API_URL, LIVE_AVAILABLE } from "./config";
import type {
  Alert, AlertQuery, CaseDetail, DashboardData, DataQuality, DatasetInfo, DatasetKey, Decision, DecisionRecord,
  Health, Metrics, Monitoring, Page, PolicyKind, SimCell, SimResult, Status, Summary,
} from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}
export interface DecideBody {
  decision: Decision;
  note: string;
  analyst: string;
}
export interface SimBody {
  dataset: DatasetKey;
  policy: PolicyKind;
  alpha: number;
  capacity_multiplier: number;
}
export interface Backend {
  mode: "demo" | "live";
  datasets(): Promise<DatasetInfo[]>;
  dashboard(ds: DatasetKey): Promise<DashboardData>;
  alerts(q: AlertQuery): Promise<Page<Alert>>;
  caseDetail(id: string): Promise<CaseDetail>;
  decide(id: string, body: DecideBody): Promise<DecisionRecord & { status: Status }>;
  metrics(ds: DatasetKey): Promise<Metrics>;
  monitoring(ds: DatasetKey): Promise<Monitoring>;
  dataQuality(ds: DatasetKey): Promise<DataQuality>;
  simulate(b: SimBody): Promise<SimResult>;
  health(): Promise<Health>;
}

const PRIORITY_ORDER: Record<string, number> = { P1: 0, P2: 1, P3: 2 };
const STORE_KEY = "rg:decisions:v1";
const MODE_KEY = "rg:mode";

/** Same filter/sort/paginate semantics as the API (backend/app/api.py). */
export function queryAlerts(all: Alert[], q: AlertQuery): Page<Alert> {
  let items = [...all];
  const ql = q.q.trim().toLowerCase();
  if (ql) items = items.filter((a) => [a.id, a.account, a.key_reason].some((s) => s.toLowerCase().includes(ql)));
  if (q.priority) items = items.filter((a) => a.priority === q.priority);
  if (q.status) items = items.filter((a) => a.status === q.status);
  const cmp: Record<AlertQuery["sort"], (a: Alert, b: Alert) => number> = {
    date: (a, b) => (a.date === b.date ? a.score - b.score : a.date < b.date ? -1 : 1),
    score: (a, b) => a.score - b.score,
    priority: (a, b) => PRIORITY_ORDER[b.priority] - PRIORITY_ORDER[a.priority] || a.score - b.score,
    amount: (a, b) => a.amounts.out_7d + a.amounts.in_7d - (b.amounts.out_7d + b.amounts.in_7d),
  };
  items.sort(cmp[q.sort]);
  if (q.order === "desc") items.reverse();
  const lo = (q.page - 1) * q.pageSize;
  return { items: items.slice(lo, lo + q.pageSize), total: items.length, page: q.page, page_size: q.pageSize };
}

function readDecisions(): Record<string, DecisionRecord[]> {
  try {
    return JSON.parse(window.localStorage.getItem(STORE_KEY) ?? "{}") as Record<string, DecisionRecord[]>;
  } catch {
    return {};
  }
}

/** Static bundle in /demo (built from real pipeline output). Decisions are stored in this browser only. */
export function createDemoBackend(base = "/demo"): Backend {
  const cache = new Map<string, Promise<unknown>>();
  const get = <T,>(path: string): Promise<T> => {
    if (!cache.has(path)) {
      const p = fetch(`${base}/${path}`).then((r) => {
        if (!r.ok) throw new ApiError(r.status, `Could not load ${path} (${r.status})`);
        return r.json();
      });
      p.catch(() => cache.delete(path));
      cache.set(path, p);
    }
    return cache.get(path) as Promise<T>;
  };
  const status = (id: string): Status => {
    const h = readDecisions()[id];
    return h && h.length ? h[h.length - 1].decision : "open";
  };
  const withStatus = (a: Alert): Alert => ({ ...a, status: status(a.id) });
  const self: Backend = {
    mode: "demo",
    datasets: async () => (await get<{ datasets: DatasetInfo[] }>("index.json")).datasets,
    async dashboard(ds) {
      const [summary, alerts] = await Promise.all([get<Summary>(`${ds}/summary.json`), get<Alert[]>(`${ds}/alerts.json`)]);
      const dec = readDecisions();
      const by: Record<string, number> = {};
      let decided = 0;
      for (const a of alerts) {
        const h = dec[a.id];
        if (h?.length) {
          decided += 1;
          const d = h[h.length - 1].decision;
          by[d] = (by[d] ?? 0) + 1;
        }
      }
      const recent = [...alerts].sort((a, b) => (a.date === b.date ? b.score - a.score : a.date < b.date ? 1 : -1)).slice(0, 8);
      return {
        summary,
        decisions: { by_decision: by, decided_in_sample: decided, open_in_sample: alerts.length - decided, sample_size: alerts.length, simulated: true },
        latest_alerts: recent.map(withStatus),
      };
    },
    async alerts(q) {
      const all = (await get<Alert[]>(`${q.dataset}/alerts.json`)).map(withStatus);
      return queryAlerts(all, q);
    },
    async caseDetail(id) {
      const m = /^RG-(LI|HI)-\d{1,6}-\d{8}$/.exec(id);
      if (!m) throw new ApiError(422, "Invalid case identifier");
      const d = (await get<Record<string, CaseDetail>>(`${m[1]}/case_details.json`))[id];
      if (!d) throw new ApiError(404, "Case not found");
      const hist = readDecisions()[id] ?? [];
      return { ...d, status: hist.length ? hist[hist.length - 1].decision : "open", decision_history: hist };
    },
    async decide(id, body) {
      await self.caseDetail(id);
      const rec: DecisionRecord = { ...body, simulated: true, created_at: new Date().toISOString() };
      const all = readDecisions();
      all[id] = [...(all[id] ?? []), rec];
      window.localStorage.setItem(STORE_KEY, JSON.stringify(all));
      return { ...rec, status: body.decision };
    },
    metrics: (ds) => get<Metrics>(`${ds}/metrics.json`),
    monitoring: (ds) => get<Monitoring>(`${ds}/monitoring.json`),
    dataQuality: (ds) => get<DataQuality>(`${ds}/data_quality.json`),
    async simulate(b) {
      const m = await get<Metrics>(`${b.dataset}/metrics.json`);
      if (b.policy === "none") {
        const base = m.h3.baseline_no_autoclose[String(b.capacity_multiplier)] ?? m.h3.baseline_no_autoclose[b.capacity_multiplier.toFixed(1)];
        if (!base) throw new ApiError(404, "Capacity setting not in precomputed grid");
        return {
          policy: "none", alpha: 0, m: b.capacity_multiplier, n_pos: m.h3.stream.n_pos, realised_miss_rate: 0, miss_ci95: null,
          review_recall: base.review_recall, unreviewed_rate: 1 - base.review_recall, expired_positive_rate: base.expired_positive_rate,
          workload_removed: 0, auto_closed_cases: 0, mean_backlog: base.mean_backlog, max_backlog: base.max_backlog, violation_rate: null,
          n_weekly_windows: 0, note: "Precomputed (no auto-close baseline).",
        };
      }
      const cell: SimCell | undefined = m.h3.same_regime.find(
        (c) => c.policy === b.policy && Math.abs(c.alpha - b.alpha) < 1e-9 && Math.abs(c.m - b.capacity_multiplier) < 1e-9,
      );
      if (!cell) throw new ApiError(404, "Setting not in the precomputed grid (live mode supports arbitrary values)");
      return { ...cell, note: "Precomputed from the recorded experiment run." };
    },
    async health() {
      return { status: "ok", version: "demo-bundle", demo_mode: true, datasets: ["LI", "HI"], model_loaded: false };
    },
  };
  return self;
}

/** FastAPI service (NEXT_PUBLIC_API_URL). */
export function createLiveBackend(base = API_URL): Backend {
  const call = async <T,>(path: string, init?: RequestInit): Promise<T> => {
    const r = await fetch(`${base}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
    if (!r.ok) {
      let msg = `${r.status}`;
      try {
        const j = await r.json();
        msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
      } catch {
        /* keep status */
      }
      throw new ApiError(r.status, msg);
    }
    return r.json() as Promise<T>;
  };
  const qs = (o: Record<string, string | number>) => new URLSearchParams(Object.entries(o).map(([k, v]) => [k, String(v)])).toString();
  return {
    mode: "live",
    datasets: async () => (await call<{ datasets: DatasetInfo[] }>("/api/datasets")).datasets,
    dashboard: (ds) => call(`/api/dashboard?dataset=${ds}`),
    alerts: (q) =>
      call(`/api/alerts?${qs({ dataset: q.dataset, q: q.q, priority: q.priority, status: q.status, sort: q.sort, order: q.order, page: q.page, page_size: q.pageSize })}`),
    caseDetail: (id) => call(`/api/cases/${encodeURIComponent(id)}`),
    decide: (id, body) => call(`/api/cases/${encodeURIComponent(id)}/decision`, { method: "POST", body: JSON.stringify(body) }),
    metrics: (ds) => call(`/api/model/metrics?dataset=${ds}`),
    monitoring: (ds) => call(`/api/monitoring?dataset=${ds}`),
    dataQuality: (ds) => call(`/api/data-quality?dataset=${ds}`),
    simulate: (b) => call("/api/simulate", { method: "POST", body: JSON.stringify(b) }),
    health: () => call("/health"),
  };
}

let current: Backend | null = null;
export function getBackend(): Backend {
  if (current) return current;
  let live = LIVE_AVAILABLE;
  if (typeof window !== "undefined" && LIVE_AVAILABLE) live = window.localStorage.getItem(MODE_KEY) !== "demo";
  current = live ? createLiveBackend() : createDemoBackend();
  return current;
}
export function setBackend(b: Backend | null): void {
  current = b;
}
export function setMode(mode: "demo" | "live"): void {
  window.localStorage.setItem(MODE_KEY, mode);
  current = null;
}
