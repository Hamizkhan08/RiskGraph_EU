import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { fixtureAlerts, installFetch, renderApp } from "./helpers";

const FORBIDDEN = /\b(guilty|criminals?|confirmed money laundering)\b/i;
const norm = (s: string) => s.replace(/[\u00a0\u202f]/g, " ");

describe("Dashboard", () => {
  it("shows KPIs computed from the recorded run, labels and the simulated-feedback card", async () => {
    installFetch();
    renderApp("/");
    expect(await screen.findByText("Review queue")).toBeInTheDocument();
    for (const l of ["Cases scored (test window)", "Review capacity", "Backlog (mean / max)", "Auto-closed cases", "Realised miss rate (auto-closed)", "Positives never reviewed", "Model health (PR-AUC)"])
      expect(screen.getByText(l)).toBeInTheDocument();
    expect(screen.getByText("317.967")).toBeInTheDocument();          // de-DE grouping of the real test-window size
    expect(screen.getAllByText("SYNTHETIC DATA").length).toBeGreaterThan(0);
    expect(screen.getAllByText("SIMULATED FEEDBACK").length).toBeGreaterThan(0);
    expect(screen.getByRole("table", { name: "Latest alerts" })).toBeInTheDocument();
  });
  it("shows a loading state, then an error with retry when the bundle cannot be loaded", async () => {
    installFetch({ fail: true });
    renderApp("/");
    expect(screen.getByRole("status")).toBeInTheDocument();
    const err = await screen.findByRole("alert");
    expect(err).toHaveTextContent(/Could not load/);
    await userEvent.click(within(err).getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});

describe("Alerts", () => {
  it("lists alerts and filters by priority, search, status; shows the no-results state and clears it", async () => {
    installFetch();
    renderApp("/alerts");
    const table = await screen.findByRole("table", { name: "Alert queue" });
    const all = fixtureAlerts();
    expect(within(table).getAllByRole("row")).toHaveLength(all.length + 1);
    await userEvent.selectOptions(screen.getByLabelText("Priority"), "P1");
    await waitFor(() => expect(within(screen.getByRole("table", { name: "Alert queue" })).getAllByRole("row")).toHaveLength(all.filter((a) => a.priority === "P1").length + 1));
    await userEvent.selectOptions(screen.getByLabelText("Priority"), "");
    await userEvent.type(screen.getByLabelText("Search"), "zzzz-nothing");
    expect(await screen.findByText("No alerts match these filters")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(await screen.findByRole("table", { name: "Alert queue" })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Status"), "suspicious");
    expect(await screen.findByText("No alerts match these filters")).toBeInTheDocument();
  });
  it("sorts, reverses the order and paginates", async () => {
    installFetch();
    renderApp("/alerts");
    await screen.findByRole("table", { name: "Alert queue" });
    await userEvent.selectOptions(screen.getByLabelText("Sort by"), "score");
    const scores = async () => (await screen.findAllByRole("row")).slice(1).map((r) => Number(norm(within(r).getAllByRole("cell")[2].textContent ?? "").split("est.")[0].replace(",", ".")));
    let s = await scores();
    expect(s).toEqual([...s].sort((a, b) => b - a));
    await userEvent.click(screen.getByRole("button", { name: /Sort order/ }));
    await waitFor(async () => { s = await scores(); expect(s).toEqual([...s].sort((a, b) => a - b)); });
    await userEvent.selectOptions(screen.getByLabelText("Per page"), "10");
    expect(await screen.findByText(/Page 1 of 2/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText(/Page 2 of 2/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });
  it("shows the empty state for an empty dataset", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => [] }) as unknown as Response));
    const { setBackend } = await import("@/lib/api");
    setBackend(null);
    renderApp("/alerts");
    expect(await screen.findByText("No alerts in this dataset")).toBeInTheDocument();
  });
  it("shows an error state with retry", async () => {
    installFetch({ fail: true });
    renderApp("/alerts");
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
  });
});

describe("Case page", () => {
  it("renders risk, grounded explanation, evidence, timeline and research annotation", async () => {
    installFetch();
    const id = fixtureAlerts()[0].id;
    renderApp(`/alerts/${id}`);
    expect(await screen.findByText("Why this case was prioritised")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: id })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Reason codes" }).children.length).toBeGreaterThan(0);
    expect(screen.getByRole("list", { name: /Top feature contributions/ }).children.length).toBeGreaterThan(0);
    expect(screen.getByRole("table", { name: "Transaction evidence" })).toBeInTheDocument();
    expect(screen.getByText("Timeline")).toBeInTheDocument();
    expect(screen.getByText(/Show synthetic ground truth/)).toBeInTheDocument();
    expect(screen.getByText("SIMULATED FEEDBACK")).toBeInTheDocument();
    expect(screen.getByText(/not a finding of wrongdoing/)).toBeInTheDocument();
  });
  it("records a simulated decision and shows it in status, history and timeline", async () => {
    installFetch();
    const id = fixtureAlerts()[0].id;
    renderApp(`/alerts/${id}`);
    await screen.findByText("Analyst decision");
    await userEvent.type(screen.getByLabelText(/Note/), "circular pattern");
    await userEvent.click(screen.getByRole("button", { name: "Suspicious" }));
    expect(await screen.findByText(/Decision recorded: Suspicious \(simulated feedback\)/)).toBeInTheDocument();
    expect(await screen.findByText(/simulated$/, { selector: "span" })).toBeInTheDocument();
    expect(await screen.findByText("circular pattern")).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem("rg:decisions:v1") ?? "{}")[id]).toHaveLength(1);
  });
  it("shows an error state for an invalid or unknown case id", async () => {
    installFetch();
    renderApp("/alerts/not-valid");
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid case identifier");
  });
});

describe("Network analysis", () => {
  it("draws the focal ego network, supports selection, labels toggle and table view", async () => {
    installFetch();
    const id = fixtureAlerts()[0].id;
    renderApp(`/network?case=${id}`);
    const g = await screen.findByRole("group", { name: "Transaction network around the focal account" });
    const nodes = within(g).getAllByRole("button", { name: /Focal account|Counterparty/ });
    expect(nodes.length).toBeGreaterThanOrEqual(2);
    expect(within(g).getAllByRole("button", { name: /Focal account/ })).toHaveLength(1);
    const before = g.querySelectorAll("text").length;
    expect(before).toBeGreaterThan(0);
    await userEvent.click(nodes[0]);
    expect(await screen.findByText("Transactions (window)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("switch", { name: "Show node labels" }));
    expect(g.querySelectorAll("text").length).toBe(0);
    await userEvent.click(screen.getByText(/Show all \d+ flows/));
    expect(screen.getByRole("table", { name: "Flows between shown accounts" })).toBeInTheDocument();
    expect(screen.getByText(/Flow, arrow = direction/)).toBeInTheDocument();
  });
});

describe("Model performance", () => {
  it("shows models, tabs, family-shift caveats and auto-close results", async () => {
    installFetch();
    renderApp("/performance");
    expect(await screen.findByText("Models on the test block")).toBeInTheDocument();
    const t = screen.getByRole("table", { name: "Model comparison" });
    expect(within(t).getAllByRole("row")).toHaveLength(7);
    expect(within(t).getByText("M3 GBM + graph (T+B+G)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /All positives/ }));
    expect(await screen.findByText(/optimistic and favours memorising/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Family shift (H2)" }));
    expect(await screen.findByText("Leave-one-family-out at m = 1")).toBeInTheDocument();
    expect(screen.getAllByText("underpowered").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("tab", { name: "Auto-close (H3)" }));
    expect(await screen.findByText("Policies at m = 1")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Held-out family auto-close results" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Calibration" }));
    expect(await screen.findByRole("table", { name: "Calibration metrics" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Ablations" }));
    expect(await screen.findByText(/Generator artefact/)).toBeInTheDocument();
  });
});

describe("Monitoring and Research", () => {
  it("labels the monitoring view as a backtest replay and shows drift and data quality", async () => {
    installFetch();
    renderApp("/monitoring");
    expect((await screen.findAllByText("BACKTEST REPLAY")).length).toBeGreaterThan(0);
    expect(screen.getByRole("table", { name: "Feature drift PSI by window" })).toBeInTheDocument();
    expect(screen.getByText("Data quality")).toBeInTheDocument();
    expect(screen.getAllByText(/not live monitoring/).length).toBeGreaterThan(0);
  });
  it("derives hypothesis outcomes from data and states what was not used", async () => {
    installFetch();
    renderApp("/research");
    expect(await screen.findByText("Research question")).toBeInTheDocument();
    const t = screen.getByRole("table", { name: "Hypotheses" });
    expect(within(t).getAllByRole("row")).toHaveLength(4);
    expect(t).toHaveTextContent(/H1/);
    expect(t).toHaveTextContent(/CI/);
    const ds = screen.getByRole("table", { name: "Datasets" });
    expect(within(ds).getByText("AMLNet v2.0").closest("tr")).toHaveTextContent("Not used.");
    expect(screen.getByText(/Not the published Zenodo release/)).toBeInTheDocument();
    expect(screen.getByText(/Responsible use:/)).toBeInTheDocument();
  });
});

describe("Settings", () => {
  it("changing capacity, policy and tolerance changes the stated outcome", async () => {
    installFetch();
    renderApp("/settings");
    const summary = async () => (await screen.findByTestId("plain-summary")).textContent ?? "";
    const first = await summary();
    expect(first).toMatch(/1×/);
    expect(first).toMatch(/Static threshold/);
    await userEvent.click(screen.getByRole("button", { name: "5×" }));
    await waitFor(async () => expect(await summary()).toMatch(/5× capacity/));
    const five = await summary();
    expect(five).not.toBe(first);
    await userEvent.click(screen.getByRole("button", { name: "C · Conformal-corrected" }));
    await userEvent.click(screen.getByRole("button", { name: /^5\s?%$/ }));
    await waitFor(async () => expect(await summary()).toMatch(/Conformal-corrected.*α = 5/));
    await userEvent.click(screen.getByRole("button", { name: "No auto-close" }));
    await waitFor(async () => expect(await summary()).toMatch(/no auto-close/));
    expect(screen.getByText("DEMO (static bundle)")).toBeInTheDocument();
    expect(screen.getByText(/No API URL is configured/)).toBeInTheDocument();
  });
});

describe("Responsible wording", () => {
  it.each(["/", "/alerts", "/performance", "/monitoring", "/research", "/settings"])("%s avoids accusatory language", async (url) => {
    installFetch();
    renderApp(url);
    await screen.findByRole("main");
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
    expect(document.body.textContent).not.toMatch(FORBIDDEN);
    expect(document.body.textContent).toMatch(/research prototype/i);
  });
});
