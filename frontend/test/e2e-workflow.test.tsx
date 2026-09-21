/**
 * End-to-end analyst workflow in jsdom (NOT a real browser):
 * Dashboard → Alerts → Alert detail → Network → Explanation → Analyst decision → Updated case state.
 */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { fixtureAlerts, installFetch, renderApp } from "./helpers";

describe("analyst workflow", () => {
  it("walks the whole journey and persists the updated case state", async () => {
    installFetch();
    const user = userEvent.setup();
    renderApp("/");
    // Dashboard
    expect(await screen.findByText("Review queue")).toBeInTheDocument();
    // → Alerts
    await user.click(within(screen.getByRole("navigation", { name: "Main" })).getByRole("link", { name: /Alerts/ }));
    const table = await screen.findByRole("table", { name: "Alert queue" });
    const firstLink = within(table).getAllByRole("link")[0];
    const id = firstLink.textContent ?? "";
    expect(fixtureAlerts().map((a) => a.id)).toContain(id);
    // → Alert detail
    await user.click(firstLink);
    expect(await screen.findByRole("heading", { name: id })).toBeInTheDocument();
    // → Network (full view)
    await user.click(screen.getByRole("link", { name: /Open full view/ }));
    expect(await screen.findByRole("group", { name: "Transaction network around the focal account" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /Case/ })).toHaveValue(id);
    // → back to the case, read the explanation
    await user.click(screen.getByRole("link", { name: /Open case/ }));
    expect(await screen.findByText("Why this case was prioritised")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Reason codes" })).toBeInTheDocument();
    // → Analyst decision
    await user.type(screen.getByLabelText(/Note/), "reviewed in e2e");
    await user.click(screen.getByRole("button", { name: "Requires review" }));
    expect(await screen.findByText(/Decision recorded: Requires review \(simulated feedback\)/)).toBeInTheDocument();
    // → Updated case state: header badge, decision history, alerts list filter, dashboard counter
    await waitFor(() => expect(screen.getByText("reviewed in e2e")).toBeInTheDocument());
    await user.click(screen.getByRole("link", { name: /Back to alerts/ }));
    await screen.findByRole("table", { name: "Alert queue" });
    await user.selectOptions(screen.getByLabelText("Status"), "requires_review");
    const filtered = await screen.findByRole("table", { name: "Alert queue" });
    await waitFor(() => expect(within(filtered).getAllByRole("row")).toHaveLength(2));
    expect(within(filtered).getByRole("link", { name: id })).toBeInTheDocument();
    await user.click(within(screen.getByRole("navigation", { name: "Main" })).getByRole("link", { name: /Dashboard/ }));
    expect(await screen.findByText(/1 of 14 sampled alerts decided/)).toBeInTheDocument();
  });
});
