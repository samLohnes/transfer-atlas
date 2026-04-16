import { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { formatFee } from "@/lib/format";
import type { PlayerTransfer, PlayerValuation } from "@/types/player";

interface ValueChartProps {
  valuations: PlayerValuation[];
  transfers: PlayerTransfer[];
}

/** Market value line chart with transfer event markers. */
export function ValueChart({ valuations, transfers }: ValueChartProps) {
  const data = useMemo(
    () => valuations.map((v) => ({
      date: v.date,
      value: v.value_eur / 100, // cents to EUR
      label: new Date(v.date).toLocaleDateString("en-US", { month: "short", year: "numeric" }),
    })),
    [valuations],
  );

  // Transfer dates for reference lines
  const transferDates = useMemo(
    () => transfers
      .filter((t) => t.transfer_date)
      .map((t) => ({
        date: t.transfer_date!,
        label: `→ ${t.to_club_name}`,
        fee: t.fee_eur,
      })),
    [transfers],
  );

  if (data.length === 0) return null;

  return (
    <div className="rounded-lg border border-white/[0.04] bg-white/[0.01] p-4">
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4ade80" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: "#6b8a78" }}
            tickLine={false}
            axisLine={{ stroke: "rgba(255,255,255,0.04)" }}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={(v: number) => formatFee(v * 100)}
            tick={{ fontSize: 10, fill: "#6b8a78" }}
            tickLine={false}
            axisLine={false}
            width={60}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(14, 31, 22, 0.95)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "12px",
              fontSize: "12px",
              color: "#e8f0ec",
            }}
            formatter={(value: unknown) => [formatFee(Number(value) * 100), "Value"]}
            labelFormatter={(label: unknown) => String(label)}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#4ade80"
            strokeWidth={2}
            fill="url(#valueGradient)"
          />
          {transferDates.map((t) => (
            <ReferenceLine
              key={t.date}
              x={new Date(t.date).toLocaleDateString("en-US", { month: "short", year: "numeric" })}
              stroke="rgba(239, 68, 68, 0.4)"
              strokeDasharray="3 3"
              label={{
                value: "●",
                position: "top",
                fill: "#ef4444",
                fontSize: 14,
              }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
      {/* Transfer legend */}
      <div className="flex items-center gap-4 mt-2 px-2">
        <div className="flex items-center gap-1.5 text-[10px] text-[#6b8a78]">
          <div className="w-3 h-0.5 bg-[#4ade80] rounded" />
          Market value
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-[#6b8a78]">
          <span className="text-red-400 text-[12px]">●</span>
          Transfer
        </div>
      </div>
    </div>
  );
}
