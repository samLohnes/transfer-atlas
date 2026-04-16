import { useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { formatFee } from "@/lib/format";
import type { PlayerTransfer, PlayerValuation } from "@/types/player";

interface ValueChartProps {
  valuations: PlayerValuation[];
  transfers: PlayerTransfer[];
}

/** Custom tooltip — shows transfer info when hovering a dot, value when hovering the line. */
function ChartTooltip({ active, payload }: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
  if (!active || !payload?.length) return null;

  // Check if any payload entry is a transfer dot
  const transferEntry = payload.find((p: any) => p.dataKey === "transferFee" && p.payload?.transfer); // eslint-disable-line @typescript-eslint/no-explicit-any
  if (transferEntry) {
    const t = transferEntry.payload.transfer as PlayerTransfer;
    return (
      <div className="rounded-xl bg-[#0e1f16]/95 backdrop-blur-xl border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.4)] px-3.5 py-2.5 text-[13px]">
        <div className="font-semibold text-[#e8f0ec]">
          {t.from_club_name} <span className="text-[#4ade80]">→</span> {t.to_club_name}
        </div>
        <div className="text-[#6b8a78] text-[11px] mt-0.5">
          {formatFee(t.fee_eur)}
        </div>
      </div>
    );
  }

  // Otherwise show market value
  const valueEntry = payload.find((p: any) => p.dataKey === "value" && p.value != null); // eslint-disable-line @typescript-eslint/no-explicit-any
  if (valueEntry) {
    return (
      <div className="rounded-xl bg-[#0e1f16]/95 backdrop-blur-xl border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.4)] px-3 py-1.5 text-[12px]">
        <span className="text-[#e8f0ec] font-data tabular-nums">{formatFee(Number(valueEntry.value) * 100)}</span>
      </div>
    );
  }

  return null;
}

/** Market value chart with transfer fee dots. */
export function ValueChart({ valuations, transfers }: ValueChartProps) {
  const data = useMemo(
    () => valuations.map((v) => ({
      date: v.date,
      value: v.value_eur / 100,
      label: new Date(v.date).toLocaleDateString("en-US", { month: "short", year: "numeric" }),
      transferFee: null as number | null,
      transfer: undefined as PlayerTransfer | undefined,
    })),
    [valuations],
  );

  const transferDots = useMemo(
    () => transfers
      .filter((t) => t.transfer_date && t.fee_eur !== null && t.fee_eur > 0 && !t.fee_is_loan)
      .map((t) => ({
        date: t.transfer_date!,
        value: null as number | null,
        transferFee: (t.fee_eur ?? 0) / 100,
        label: new Date(t.transfer_date!).toLocaleDateString("en-US", { month: "short", year: "numeric" }),
        transfer: t,
      })),
    [transfers],
  );

  const mergedData = useMemo(() => {
    const all = [...data, ...transferDots];
    all.sort((a, b) => a.date.localeCompare(b.date));
    return all;
  }, [data, transferDots]);

  if (data.length === 0) return null;

  return (
    <div className="rounded-lg border border-white/[0.04] bg-white/[0.01] p-4">
      <ResponsiveContainer width="100%" height={250}>
        <ComposedChart data={mergedData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
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
          <Tooltip content={<ChartTooltip />} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#4ade80"
            strokeWidth={2}
            fill="url(#valueGradient)"
            connectNulls
          />
          <Scatter dataKey="transferFee" fill="#ef4444" r={6} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 mt-2 px-2">
        <div className="flex items-center gap-1.5 text-[10px] text-[#6b8a78]">
          <div className="w-3 h-0.5 bg-[#4ade80] rounded" />
          Market value
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-[#6b8a78]">
          <span className="text-red-400 text-[12px]">●</span>
          Transfer fee
        </div>
      </div>
    </div>
  );
}
