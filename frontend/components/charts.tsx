"use client";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

export interface Series {
  key: string;
  label: string;
  color: string;
  dash?: string;
}

/* Mastercard-inspired warm palette — no neon, no cyan */
export const COLORS = {
  navy:   "#141413",   /* Ink Black — primary series */
  blue:   "#3860BE",   /* Link Blue — secondary series */
  teal:   "#2D7D6F",   /* Muted teal */
  slate:  "#696969",   /* Slate Gray */
  amber:  "#9A3A0A",   /* Clay Brown — warning series */
  red:    "#CF4500",   /* Signal Orange — alert / danger */
  green:  "#1a6e3c",   /* Warm green */
  coral:  "#F37338",   /* Light Signal Orange — decorative */
  purple: "#5B4A8A",   /* Muted violet */
};

const axis = {
  fontSize: 11,
  fill: "#696969",
  fontFamily: "'Sofia Sans', 'Inter', sans-serif",
  fontWeight: 500,
};

/* Warm cream tooltip — Mastercard editorial feel */
const WarmTooltip = ({
  active, payload, label, labelFormatter, formatter,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string | number;
  labelFormatter?: (l: string | number) => string;
  formatter?: (v: number) => string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#FFFFFF",
      border: "1px solid rgba(20,20,19,0.12)",
      borderRadius: 16,
      padding: "10px 14px",
      boxShadow: "rgba(0,0,0,0.10) 0px 16px 32px 0px",
      fontFamily: "'Sofia Sans','Inter',sans-serif",
      fontSize: 12,
      minWidth: 120,
    }}>
      <p style={{ color: "#696969", marginBottom: 6, fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase" }}>
        {labelFormatter ? labelFormatter(label ?? "") : label}
      </p>
      {payload.map((p) => (
        <p key={p.name} style={{ margin: "3px 0", display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: p.color, flexShrink: 0 }} />
          <span style={{ color: "#555555" }}>{p.name}:</span>
          <span style={{ color: "#141413", fontWeight: 500 }}>{formatter ? formatter(p.value) : p.value}</span>
        </p>
      ))}
    </div>
  );
};

export function LineSeries({
  data, xKey, series, height = 260, yFormat, xFormat,
  ariaLabel, yDomain, refY, xType = "category",
}: {
  data: Record<string, number | string | null>[];
  xKey: string;
  series: Series[];
  height?: number;
  yFormat?: (v: number) => string;
  xFormat?: (v: number | string) => string;
  ariaLabel: string;
  yDomain?: [number | "auto", number | "auto"];
  refY?: { y: number; label: string };
  xType?: "category" | "number";
}) {
  return (
    <div role="img" aria-label={ariaLabel} style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 600, height }}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="rgba(20,20,19,0.06)" strokeDasharray="4 4" />
          <XAxis
            dataKey={xKey} type={xType} tick={axis} tickFormatter={xFormat} minTickGap={24}
            axisLine={{ stroke: "rgba(20,20,19,0.12)" }} tickLine={false}
          />
          <YAxis
            tick={axis} tickFormatter={yFormat} domain={yDomain} width={56}
            axisLine={false} tickLine={false}
          />
          <Tooltip content={<WarmTooltip labelFormatter={xFormat} formatter={yFormat} />} />
          {series.length > 1 && (
            <Legend wrapperStyle={{ fontSize: 12, color: "#696969", fontFamily: "'Sofia Sans','Inter',sans-serif" }} />
          )}
          {refY && (
            <ReferenceLine
              y={refY.y} stroke={COLORS.red} strokeDasharray="5 3"
              label={{ value: refY.label, fontSize: 11, fill: COLORS.red, position: "insideTopRight" }}
            />
          )}
          {series.map((s) => (
            <Line
              key={s.key} type="monotone" dataKey={s.key} name={s.label}
              stroke={s.color} strokeDasharray={s.dash} dot={false}
              strokeWidth={2} connectNulls isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BarSeries({
  data, xKey, series, height = 260, yFormat, xFormat,
  ariaLabel, stacked, refY, layout = "horizontal",
}: {
  data: Record<string, number | string | null>[];
  xKey: string;
  series: Series[];
  height?: number;
  yFormat?: (v: number) => string;
  xFormat?: (v: number | string) => string;
  ariaLabel: string;
  stacked?: boolean;
  refY?: { y: number; label: string };
  layout?: "horizontal" | "vertical";
}) {
  const vertical = layout === "vertical";
  return (
    <div role="img" aria-label={ariaLabel} style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 600, height }}>
        <BarChart data={data} layout={layout} margin={{ top: 8, right: 16, bottom: 4, left: vertical ? 90 : 4 }}>
          <CartesianGrid stroke="rgba(20,20,19,0.06)" strokeDasharray="4 4" />
          {vertical ? (
            <>
              <XAxis type="number" tick={axis} tickFormatter={yFormat} axisLine={{ stroke: "rgba(20,20,19,0.12)" }} tickLine={false} />
              <YAxis type="category" dataKey={xKey} tick={axis} width={120} axisLine={false} tickLine={false} />
            </>
          ) : (
            <>
              <XAxis dataKey={xKey} tick={axis} tickFormatter={xFormat} minTickGap={16} axisLine={{ stroke: "rgba(20,20,19,0.12)" }} tickLine={false} />
              <YAxis tick={axis} tickFormatter={yFormat} width={56} axisLine={false} tickLine={false} />
            </>
          )}
          <Tooltip content={<WarmTooltip labelFormatter={xFormat} formatter={yFormat} />} />
          {series.length > 1 && (
            <Legend wrapperStyle={{ fontSize: 12, color: "#696969", fontFamily: "'Sofia Sans','Inter',sans-serif" }} />
          )}
          {refY && (
            <ReferenceLine
              y={refY.y} stroke={COLORS.red} strokeDasharray="5 3"
              label={{ value: refY.label, fontSize: 11, fill: COLORS.red }}
            />
          )}
          {series.map((s) => (
            <Bar
              key={s.key} dataKey={s.key} name={s.label} fill={s.color}
              stackId={stacked ? "a" : undefined} isAnimationActive={false}
              radius={[3, 3, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
