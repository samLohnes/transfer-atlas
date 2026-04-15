import { formatFee, formatCount } from "@/lib/format";

interface TooltipData {
  type: "country" | "arc";
  x: number;
  y: number;
  // Country tooltip
  countryName?: string;
  netSpend?: number;
  totalTransfers?: number;
  // Arc tooltip
  fromCountry?: string;
  toCountry?: string;
  fee?: number;
  transferCount?: number;
}

interface MapTooltipProps {
  data: TooltipData | null;
}

/** Positioned tooltip for map hover states. */
export function MapTooltip({ data }: MapTooltipProps) {
  if (!data) return null;

  return (
    <div
      className="pointer-events-none fixed z-50 rounded-lg bg-[#1e3a2a] border border-[#2d4a38] px-3 py-2 shadow-lg text-sm"
      style={{ left: data.x + 12, top: data.y - 12 }}
    >
      {data.type === "country" ? (
        <>
          <div className="font-medium text-[#e8f0ec]">{data.countryName}</div>
          <div className="text-[#8fa898] mt-0.5">
            Net Spend: <span className="tabular-nums">{formatFee(data.netSpend ?? null)}</span>
          </div>
          <div className="text-[#8fa898]">
            Transfers: <span className="tabular-nums">{formatCount(data.totalTransfers ?? 0)}</span>
          </div>
        </>
      ) : (
        <>
          <div className="font-medium text-[#e8f0ec]">
            {data.fromCountry} → {data.toCountry}
          </div>
          <div className="text-[#8fa898] mt-0.5">
            <span className="tabular-nums">{formatFee(data.fee ?? null)}</span>
            {" · "}
            <span className="tabular-nums">{formatCount(data.transferCount ?? 0)}</span> transfers
          </div>
        </>
      )}
    </div>
  );
}

export type { TooltipData };
