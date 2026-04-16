import { formatFee } from "@/lib/format";
import type { PlayerTransfer } from "@/types/player";

interface CareerTimelineProps {
  transfers: PlayerTransfer[];
}

/** Horizontal career path showing club stops with transfer fees between them. */
export function CareerTimeline({ transfers }: CareerTimelineProps) {
  // Build ordered list of club stints from transfers
  const stops: { clubName: string; years: string; feeIn: number | null; isLoan: boolean }[] = [];

  for (let i = 0; i < transfers.length; i++) {
    const t = transfers[i];
    // Add the "from" club as first stop if this is the first transfer
    if (i === 0) {
      const startYear = t.transfer_date ? t.transfer_date.slice(0, 4) : t.season.split("-")[0];
      stops.push({ clubName: t.from_club_name, years: `...–${startYear}`, feeIn: null, isLoan: false });
    }

    const year = t.transfer_date ? t.transfer_date.slice(0, 4) : t.season.split("-")[0];
    const nextTransfer = transfers[i + 1];
    const endYear = nextTransfer
      ? (nextTransfer.transfer_date ? nextTransfer.transfer_date.slice(0, 4) : nextTransfer.season.split("-")[0])
      : "Present";

    stops.push({
      clubName: t.to_club_name,
      years: `${year}–${endYear}`,
      feeIn: t.fee_eur,
      isLoan: t.fee_is_loan,
    });
  }

  return (
    <div className="flex items-center gap-0 overflow-x-auto pb-2">
      {stops.map((stop, i) => (
        <div key={i} className="flex items-center shrink-0">
          {/* Fee connector (not for first stop) */}
          {i > 0 && (
            <div className="flex flex-col items-center mx-1">
              <span className="font-data text-[10px] tabular-nums text-[#4ade80]/70 whitespace-nowrap mb-0.5">
                {stop.isLoan ? "Loan" : formatFee(stop.feeIn)}
              </span>
              <div className="w-12 h-px bg-[#4ade80]/30 relative">
                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-0 h-0 border-l-[4px] border-l-[#4ade80]/30 border-y-[3px] border-y-transparent" />
              </div>
            </div>
          )}

          {/* Club stop */}
          <div className="flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center mb-1">
              <span className="text-[11px] font-bold text-[#c5dace]">
                {stop.clubName.split(" ").map((w) => w[0]).join("").slice(0, 3)}
              </span>
            </div>
            <span className="text-[11px] text-[#e8f0ec] font-medium text-center max-w-[80px] leading-tight">
              {stop.clubName}
            </span>
            <span className="font-data text-[9px] text-[#6b8a78] tabular-nums mt-0.5">
              {stop.years}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
