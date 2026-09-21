/** European formatting: numbers 1.234,56 · dates dd/mm/yyyy · 24 h times · UTC (dataset time is synthetic). */
export function parseTs(s: string): Date {
  const iso = s.includes("T") ? s : s.replace(" ", "T");
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
}
export function fmtNum(v: number, d = 2): string {
  return new Intl.NumberFormat("de-DE", { maximumFractionDigits: d }).format(v);
}
export function fmtFixed(v: number, d = 2): string {
  return new Intl.NumberFormat("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
}
export function fmtPct(v: number, d = 1): string {
  return new Intl.NumberFormat("de-DE", { style: "percent", minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
}
export function fmtMoney(v: number, currency: string): string {
  try {
    return new Intl.NumberFormat("de-DE", { style: "currency", currency }).format(v);
  } catch {
    return `${fmtFixed(v, 2)} ${currency}`;
  }
}
export function fmtDate(s: string): string {
  return new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", day: "2-digit", month: "2-digit", year: "numeric" }).format(parseTs(s));
}
export function fmtDateTime(s: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parseTs(s));
}
export function fmtCI(ci: [number, number] | null | undefined, pct = true): string {
  if (!ci) return "n/a";
  return pct ? `${fmtPct(ci[0])} – ${fmtPct(ci[1])}` : `${fmtFixed(ci[0], 3)} – ${fmtFixed(ci[1], 3)}`;
}
export const PRIORITY_LABEL: Record<string, string> = { P1: "Priority 1", P2: "Priority 2", P3: "Priority 3" };
export const STATUS_LABEL: Record<string, string> = {
  open: "Open",
  suspicious: "Suspicious",
  false_positive: "False positive",
  requires_review: "Requires review",
};
