import { render } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import { vi } from "vitest";
import Alerts from "@/app/alerts/page";
import Case from "@/app/alerts/[id]/page";
import Dashboard from "@/app/page";
import Monitoring from "@/app/monitoring/page";
import Network from "@/app/network/page";
import Performance from "@/app/performance/page";
import Research from "@/app/research/page";
import Settings from "@/app/settings/page";
import { AppShell } from "@/components/AppShell";
import { setBackend } from "@/lib/api";
import { nav, usePathname } from "./navMock";

const FIX = path.resolve(__dirname, "fixtures");

/** Stub fetch: /demo/<file> served from test/fixtures; anything else 404. `fail` forces a 500. */
export function installFetch(opts: { fail?: boolean } = {}) {
  const fn = vi.fn(async (input: RequestInfo | URL) => {
    const u = String(input);
    const m = /\/demo\/(.+)$/.exec(u);
    const file = m ? path.join(FIX, m[1]) : "";
    if (opts.fail) return { ok: false, status: 500, json: async () => ({}) } as Response;
    if (m && fs.existsSync(file)) return { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(file, "utf8")) } as Response;
    return { ok: false, status: 404, json: async () => ({}) } as Response;
  });
  vi.stubGlobal("fetch", fn);
  setBackend(null);
  return fn;
}
export const fixtureAlerts = (): { id: string; priority: string; score: number }[] => JSON.parse(fs.readFileSync(path.join(FIX, "LI", "alerts.json"), "utf8"));

function Routes() {
  const p = usePathname();
  if (p === "/") return <Dashboard />;
  if (p === "/alerts") return <Alerts />;
  if (p.startsWith("/alerts/")) return <Case />;
  if (p === "/network") return <Network />;
  if (p === "/performance") return <Performance />;
  if (p === "/monitoring") return <Monitoring />;
  if (p === "/research") return <Research />;
  if (p === "/settings") return <Settings />;
  return <p>not found</p>;
}
export function renderApp(url = "/") {
  nav.reset(url);
  return render(
    <AppShell>
      <Routes />
    </AppShell>,
  );
}
