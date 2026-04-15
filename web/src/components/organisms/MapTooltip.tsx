import { formatFee, formatCount } from "@/lib/format";

interface TooltipData {
  type: "country" | "arc";
  x: number;
  y: number;
  countryName?: string;
  netSpend?: number;
  totalTransfers?: number;
  fromCountry?: string;
  toCountry?: string;
  fee?: number;
  transferCount?: number;
}

interface MapTooltipProps {
  data: TooltipData | null;
}

/** Frosted-glass positioned tooltip for map hover states. */
export function MapTooltip({ data }: MapTooltipProps) {
  if (!data) return null;

  return (
    <div
      className="pointer-events-none fixed z-50 rounded-xl bg-[#0e1f16]/90 backdrop-blur-xl border border-white/[0.08] px-3.5 py-2.5 shadow-[0_8px_32px_rgba(0,0,0,0.4)] text-[13px]"
      style={{ left: data.x + 14, top: data.y - 14 }}
    >
      {data.type === "country" ? (
        <>
          <div className="font-semibold text-[#e8f0ec] tracking-tight">{data.countryName}</div>
          <div className="text-[#6b8a78] mt-1 space-y-0.5">
            <div>Net Spend: <span className="font-data text-[#c5dace] tabular-nums">{formatFee(data.netSpend ?? null)}</span></div>
            <div>Transfers: <span className="font-data text-[#c5dace] tabular-nums">{formatCount(data.totalTransfers ?? 0)}</span></div>
          </div>
        </>
      ) : (
        <>
          <div className="font-semibold text-[#e8f0ec] tracking-tight">
            {data.fromCountry} <span className="text-[#4ade80]">→</span> {data.toCountry}
          </div>
          <div className="text-[#6b8a78] mt-1">
            <span className="font-data text-[#c5dace] tabular-nums">{formatFee(data.fee ?? null)}</span>
            <span className="mx-1.5 text-white/10">|</span>
            <span className="font-data text-[#c5dace] tabular-nums">{formatCount(data.transferCount ?? 0)}</span> transfers
          </div>
        </>
      )}
    </div>
  );
}

export type { TooltipData };
