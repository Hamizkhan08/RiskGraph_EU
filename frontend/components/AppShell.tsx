"use client";
import { Activity, BookOpen, Gauge, LayoutDashboard, ListChecks, Network, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { getBackend } from "@/lib/api";
import { DISCLOSURE } from "@/lib/config";
import { DatasetProvider, useDataset } from "@/lib/hooks";
import type { DatasetKey } from "@/lib/types";
import { Badge, cn } from "./ui";

export const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/alerts", label: "Alerts", icon: ListChecks },
  { href: "/network", label: "Network analysis", icon: Network },
  { href: "/performance", label: "Model performance", icon: Gauge },
  { href: "/monitoring", label: "Monitoring", icon: Activity },
  { href: "/research", label: "Research", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
];

/* Mastercard-style eyebrow dot */
function EyebrowDot() {
  return (
    <span
      aria-hidden
      style={{
        display: "inline-block",
        width: 5,
        height: 5,
        borderRadius: "50%",
        background: "var(--light-orange)",
        marginRight: 6,
        flexShrink: 0,
        verticalAlign: "middle",
      }}
    />
  );
}

/* Mastercard Overlapping Circles Logo Mark */
function MCMark() {
  return (
    <svg width="32" height="22" viewBox="0 0 32 22" fill="none" aria-hidden>
      <circle cx="11" cy="11" r="11" fill="#EB001B" />
      <circle cx="21" cy="11" r="11" fill="#F79E1B" />
      <path
        d="M16 3.6a11 11 0 0 1 0 14.8A11 11 0 0 1 16 3.6Z"
        fill="#FF5F00"
      />
    </svg>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const { dataset, setDataset } = useDataset();
  const [mode, setMode] = useState<"demo" | "live">("demo");
  useEffect(() => {
    queueMicrotask(() => setMode(getBackend().mode));
  }, []);

  return (
    <div className="min-h-screen" style={{ background: "var(--canvas-cream)", color: "var(--ink-black)" }}>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-3 focus:text-sm"
        style={{ background: "var(--white)", color: "var(--ink-black)", borderRadius: "var(--radius-btn)", top: 8, left: 8 }}
      >
        Skip to content
      </a>

      {/* Research prototype banner */}
      <div
        className="flex flex-wrap items-center justify-center gap-2 px-4 py-2 text-center text-xs"
        style={{ background: "var(--ink-black)", color: "var(--canvas-cream)" }}
      >
        <EyebrowDot />
        <span className="font-bold tracking-widest uppercase" style={{ letterSpacing: "0.06em", fontSize: 11 }}>
          Research Prototype
        </span>
        <span style={{ opacity: 0.4 }}>·</span>
        <span style={{ opacity: 0.7 }}>Synthetic data — not a detection system</span>
        <span style={{ opacity: 0.4 }}>·</span>
        <span style={{ opacity: 0.7 }}>
          {mode === "demo" ? "Demo mode — decisions stored in browser only" : "Live API — decisions recorded"}
        </span>
      </div>

      <div className="mx-auto flex max-w-[1500px] flex-col md:flex-row">
        {/* Sidebar — cream canvas with ink pill active states */}
        <nav
          aria-label="Main"
          className="md:min-h-[calc(100vh-36px)] md:w-64 md:shrink-0"
          style={{
            background: "var(--canvas-cream)",
            borderRight: "1px solid var(--border-ink)",
          }}
        >
          {/* Logo */}
          <div className="flex items-center gap-3 px-5 py-5" style={{ borderBottom: "1px solid var(--border-ink)" }}>
            <MCMark />
            <div>
              <p
                className="text-sm font-semibold leading-tight"
                style={{ color: "var(--ink-black)", letterSpacing: "-0.01em" }}
              >
                RiskGraph EU
              </p>
              <p className="mc-eyebrow" style={{ fontSize: 10, marginTop: 2, color: "var(--slate-gray)" }}>
                <EyebrowDot />Alert Prioritisation
              </p>
            </div>
          </div>

          {/* Nav items */}
          <ul className="flex gap-1 overflow-x-auto p-3 md:flex-col md:gap-1">
            {NAV.map(({ href, label, icon: Icon }) => {
              const active = href === "/" ? path === "/" : path?.startsWith(href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2.5 whitespace-nowrap px-4 py-2.5 text-sm transition-all duration-150 focus-visible:outline-2",
                    )}
                    style={
                      active
                        ? {
                            background: "var(--ink-black)",
                            color: "var(--canvas-cream)",
                            borderRadius: "var(--radius-pill)",
                            fontWeight: 500,
                            letterSpacing: "-0.01em",
                          }
                        : {
                            background: "transparent",
                            color: "var(--slate-gray)",
                            borderRadius: "var(--radius-pill)",
                            fontWeight: 400,
                          }
                    }
                    onMouseEnter={(e) => {
                      if (!active) {
                        const el = e.currentTarget as HTMLElement;
                        el.style.background = "rgba(20,20,19,0.06)";
                        el.style.color = "var(--ink-black)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!active) {
                        const el = e.currentTarget as HTMLElement;
                        el.style.background = "transparent";
                        el.style.color = "var(--slate-gray)";
                      }
                    }}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden />
                    <span>{label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Main content */}
        <div className="min-w-0 flex-1">
          {/* Sticky header — white pill-feel with soft shadow */}
          <header
            className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 px-6 py-3"
            style={{
              background: "var(--bg-header)",
              backdropFilter: "blur(16px)",
              WebkitBackdropFilter: "blur(16px)",
              borderBottom: "1px solid var(--border-ink)",
            }}
          >
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="warn">SYNTHETIC DATA</Badge>
              <Badge tone="brand">PUBLIC GENERATOR (Tide, MIT)</Badge>
              {mode === "demo" && <Badge tone="neutral">DEMO MODE</Badge>}
            </div>
            <label
              className="flex items-center gap-2 text-sm"
              style={{ color: "var(--slate-gray)", fontWeight: 500 }}
            >
              Condition
              <select
                value={dataset}
                onChange={(e) => setDataset(e.target.value as DatasetKey)}
                className="text-sm"
                style={{
                  background: "var(--white)",
                  border: "1.5px solid var(--border-ink-strong)",
                  color: "var(--ink-black)",
                  borderRadius: "var(--radius-btn)",
                  padding: "4px 12px",
                  fontFamily: "inherit",
                  cursor: "pointer",
                }}
                aria-label="Dataset condition"
              >
                <option value="LI">LI — low illicit ratio (~0.10 %)</option>
                <option value="HI">HI — high illicit ratio (~0.20 %)</option>
              </select>
            </label>
          </header>

          <main id="main" className="px-6 py-7" tabIndex={-1}>
            {children}
          </main>

          {/* Footer — Ink Black, Mastercard-style */}
          <footer
            className="px-6 py-8"
            style={{
              background: "var(--ink-black)",
              color: "rgba(252, 251, 250, 0.7)",
              fontSize: 13,
            }}
          >
            <p style={{ color: "var(--canvas-cream)", fontWeight: 500, fontSize: 14, marginBottom: 8 }}>
              RiskGraph EU
            </p>
            <p className="max-w-4xl" style={{ lineHeight: 1.6 }}>{DISCLOSURE}</p>
            <p className="mt-2" style={{ color: "rgba(252,251,250,0.45)", fontSize: 12 }}>
              Elevated risk, prioritised case and requires review are model outputs on synthetic data — never a finding that any offence occurred.
            </p>
          </footer>
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children, initial }: { children: ReactNode; initial?: DatasetKey }) {
  return (
    <DatasetProvider initial={initial}>
      <Shell>{children}</Shell>
    </DatasetProvider>
  );
}
