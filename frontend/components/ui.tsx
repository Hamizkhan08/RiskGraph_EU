"use client";
import clsx, { type ClassValue } from "clsx";
import { AlertTriangle, Inbox, SearchX } from "lucide-react";
import type { ReactNode } from "react";
import type { AsyncState } from "@/lib/hooks";

export const cn = (...v: ClassValue[]) => clsx(v);

/* ─── Badge ──────────────────────────────────────────────────────────────── */
type Tone = "neutral" | "brand" | "info" | "success" | "warn" | "danger";

const BADGE_STYLES: Record<Tone, { background: string; color: string; border: string }> = {
  neutral: { background: "rgba(20,20,19,0.07)", color: "var(--charcoal)", border: "1px solid rgba(20,20,19,0.15)" },
  brand:   { background: "rgba(243,115,56,0.10)", color: "var(--clay-brown)", border: "1px solid rgba(243,115,56,0.25)" },
  info:    { background: "rgba(56,96,190,0.08)", color: "var(--link-blue)", border: "1px solid rgba(56,96,190,0.20)" },
  success: { background: "rgba(34,139,72,0.08)", color: "#1a6e3c", border: "1px solid rgba(34,139,72,0.20)" },
  warn:    { background: "rgba(207,69,0,0.08)", color: "var(--signal-orange)", border: "1px solid rgba(207,69,0,0.22)" },
  danger:  { background: "rgba(185,28,28,0.07)", color: "#991b1b", border: "1px solid rgba(185,28,28,0.18)" },
};

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  const s = BADGE_STYLES[tone];
  return (
    <span
      title={title}
      className="inline-flex items-center gap-1 whitespace-nowrap font-medium"
      style={{
        background: s.background,
        color: s.color,
        border: s.border,
        borderRadius: "var(--radius-pill)",
        padding: "3px 10px",
        fontSize: 11,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        fontWeight: 700,
      }}
    >
      {children}
    </span>
  );
}

export const PRIORITY_TONE: Record<string, Tone> = { P1: "danger", P2: "warn", P3: "neutral" };
export const STATUS_TONE: Record<string, Tone> = { open: "info", suspicious: "danger", false_positive: "success", requires_review: "warn" };

/* ─── Card ───────────────────────────────────────────────────────────────── */
export function Card({ title, subtitle, actions, children, className, id }: {
  title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; id?: string;
}) {
  return (
    <section
      id={id}
      aria-labelledby={id ? `${id}-h` : undefined}
      className={cn("animate-fade-in-up", className)}
      style={{
        background: "var(--lifted-cream)",
        borderRadius: "var(--radius-card)",
        border: "1px solid var(--border-ink)",
        boxShadow: "var(--shadow-sm)",
        overflow: "hidden",
      }}
    >
      {(title || actions) && (
        <header
          className="flex flex-wrap items-start justify-between gap-2 px-5 py-4"
          style={{ borderBottom: "1px solid var(--border-ink)" }}
        >
          <div>
            {title && (
              <h2
                id={id ? `${id}-h` : undefined}
                className="text-sm font-semibold"
                style={{ color: "var(--ink-black)", letterSpacing: "-0.01em" }}
              >
                {title}
              </h2>
            )}
            {subtitle && (
              <p className="mt-0.5 text-xs" style={{ color: "var(--slate-gray)" }}>{subtitle}</p>
            )}
          </div>
          {actions}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

/* ─── Stat ───────────────────────────────────────────────────────────────── */
export function Stat({ label, value, hint, tone }: { label: string; value: ReactNode; hint?: ReactNode; tone?: "warn" | "danger" }) {
  /* Eyebrow accent dot color matches tone */
  const dotColor = tone === "danger" ? "var(--signal-orange)" : tone === "warn" ? "var(--light-orange)" : "var(--light-orange)";
  const valueColor = tone === "danger" ? "var(--signal-orange)" : tone === "warn" ? "var(--clay-brown)" : "var(--ink-black)";

  return (
    <div
      className="animate-fade-in-up"
      style={{
        background: "var(--lifted-cream)",
        borderRadius: "var(--radius-card)",
        border: "1px solid var(--border-ink)",
        boxShadow: "var(--shadow-sm)",
        padding: "20px 24px 20px",
        overflow: "hidden",
      }}
    >
      {/* Eyebrow label with dot */}
      <dt
        style={{
          display: "flex",
          alignItems: "center",
          gap: 5,
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.05em",
          textTransform: "uppercase",
          color: "var(--slate-gray)",
          marginBottom: 8,
        }}
      >
        <span
          aria-hidden
          style={{
            display: "inline-block",
            width: 5,
            height: 5,
            borderRadius: "50%",
            background: dotColor,
            flexShrink: 0,
          }}
        />
        {label}
      </dt>
      <dd
        style={{
          fontSize: 28,
          fontWeight: 500,
          letterSpacing: "-0.02em",
          color: valueColor,
          lineHeight: 1.1,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {value}
      </dd>
      {hint && (
        <p style={{ marginTop: 6, fontSize: 12, color: "var(--slate-gray)", lineHeight: 1.4 }}>{hint}</p>
      )}
    </div>
  );
}

/* ─── PageHeader ─────────────────────────────────────────────────────────── */
export function PageHeader({ title, subtitle, right }: { title: string; subtitle?: ReactNode; right?: ReactNode }) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
      <div>
        <p
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            color: "var(--slate-gray)",
            display: "flex",
            alignItems: "center",
            gap: 5,
            marginBottom: 6,
          }}
        >
          <span
            aria-hidden
            style={{
              display: "inline-block",
              width: 5,
              height: 5,
              borderRadius: "50%",
              background: "var(--light-orange)",
              flexShrink: 0,
            }}
          />
          RiskGraph EU
        </p>
        <h1
          style={{
            fontSize: 32,
            fontWeight: 500,
            letterSpacing: "-0.02em",
            color: "var(--ink-black)",
            lineHeight: 1.15,
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p className="mt-2 max-w-3xl" style={{ fontSize: 15, color: "var(--slate-gray)", lineHeight: 1.5 }}>
            {subtitle}
          </p>
        )}
      </div>
      {right}
    </div>
  );
}

/* ─── Notice ─────────────────────────────────────────────────────────────── */
export function Notice({ tone = "info", title, children }: { tone?: "info" | "warn" | "danger"; title?: string; children: ReactNode }) {
  const styles = {
    info:   { background: "rgba(56,96,190,0.06)",  borderLeft: "3px solid var(--link-blue)",     color: "var(--charcoal)" },
    warn:   { background: "rgba(243,115,56,0.07)", borderLeft: "3px solid var(--light-orange)",  color: "var(--charcoal)" },
    danger: { background: "rgba(207,69,0,0.06)",   borderLeft: "3px solid var(--signal-orange)", color: "var(--charcoal)" },
  }[tone];
  return (
    <div
      role="note"
      className="text-sm"
      style={{
        ...styles,
        borderRadius: 12,
        padding: "10px 14px",
        border: "1px solid rgba(20,20,19,0.08)",
      }}
    >
      {title && <strong className="mr-1" style={{ color: "var(--ink-black)" }}>{title}</strong>}
      {children}
    </div>
  );
}

/* ─── Loading ────────────────────────────────────────────────────────────── */
export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-4 p-2">
      <span className="sr-only">{label}</span>
      {[33, 100, 66].map((w, i) => (
        <div
          key={i}
          className="rounded-2xl animate-shimmer"
          style={{
            height: i === 1 ? 100 : 18,
            width: `${w}%`,
            background: "linear-gradient(90deg, var(--canvas-cream) 25%, var(--soft-bone) 50%, var(--canvas-cream) 75%)",
            backgroundSize: "600px 100%",
          }}
        />
      ))}
    </div>
  );
}

/* ─── ErrorState ─────────────────────────────────────────────────────────── */
export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 p-4 text-sm"
      style={{
        background: "rgba(207,69,0,0.06)",
        border: "1px solid rgba(207,69,0,0.20)",
        borderLeft: "3px solid var(--signal-orange)",
        borderRadius: 16,
        color: "var(--charcoal)",
      }}
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--signal-orange)" }} aria-hidden />
      <div>
        <p className="font-semibold" style={{ color: "var(--ink-black)" }}>Something went wrong</p>
        <p className="mt-1 break-words">{error.message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-3"
            style={{
              background: "var(--ink-black)",
              color: "var(--canvas-cream)",
              border: "none",
              borderRadius: "var(--radius-btn)",
              padding: "6px 20px",
              fontSize: 13,
              fontWeight: 500,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

/* ─── EmptyState ─────────────────────────────────────────────────────────── */
export function EmptyState({ title, body, action, kind = "empty" }: {
  title: string; body?: ReactNode; action?: ReactNode; kind?: "empty" | "no-results";
}) {
  const Icon = kind === "empty" ? Inbox : SearchX;
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-center">
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: "50%",
          background: "var(--soft-bone)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Icon className="h-6 w-6" style={{ color: "var(--dust-taupe)" }} aria-hidden />
      </div>
      <p className="font-semibold" style={{ color: "var(--ink-black)", letterSpacing: "-0.01em" }}>{title}</p>
      {body && <p className="max-w-md text-sm" style={{ color: "var(--slate-gray)" }}>{body}</p>}
      {action}
    </div>
  );
}

/* ─── Async ──────────────────────────────────────────────────────────────── */
export function Async<T>({ state, children, label }: {
  state: AsyncState<T> & { reload: () => void };
  children: (d: T) => ReactNode;
  label?: string;
}) {
  if (state.status === "loading") return <Loading label={label} />;
  if (state.status === "error") return <ErrorState error={state.error} onRetry={state.reload} />;
  return <>{children(state.data)}</>;
}

/* ─── Table primitives ───────────────────────────────────────────────────── */
export const Th = ({ children, className, ...p }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
  <th
    scope="col"
    className={cn("whitespace-nowrap px-4 py-3 text-left", className)}
    style={{
      background: "var(--canvas-cream)",
      color: "var(--slate-gray)",
      borderBottom: "1px solid var(--border-ink)",
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: "0.05em",
      textTransform: "uppercase",
    }}
    {...p}
  >
    {children}
  </th>
);

export const Td = ({ children, className, ...p }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
  <td
    className={cn("px-4 py-3 align-top text-sm", className)}
    style={{ borderBottom: "1px solid var(--border-ink)", color: "var(--charcoal)" }}
    {...p}
  >
    {children}
  </td>
);

export function TableWrap({ children, caption }: { children: ReactNode; caption: string }) {
  return (
    <div
      className="overflow-x-auto"
      style={{
        borderRadius: "var(--radius-card)",
        border: "1px solid var(--border-ink)",
        overflow: "hidden",
      }}
    >
      <table className="min-w-full border-collapse">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function DataLabels({ demo }: { demo: boolean }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <Badge tone="warn">SYNTHETIC DATA</Badge>
      {demo && <Badge tone="neutral">DEMO MODE</Badge>}
    </div>
  );
}
