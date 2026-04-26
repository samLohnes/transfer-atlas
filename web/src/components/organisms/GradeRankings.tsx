import { Link } from "react-router-dom";
import { GradeBadge } from "@/components/atoms/GradeBadge";
import { EmptyState } from "@/components/molecules/EmptyState";
import { formatFee } from "@/lib/format";
import { getGradeColors } from "@/lib/gradeColors";
import type { RankedTransfer } from "@/types/grade";

interface GradeRankingsProps {
  best: RankedTransfer[];
  worst: RankedTransfer[];
  loading: boolean;
}

/** Side-by-side best / worst ranking panels for the Grades page. */
export function GradeRankings({ best, worst, loading }: GradeRankingsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <RankingPanel category="best" transfers={best} loading={loading} />
      <RankingPanel category="worst" transfers={worst} loading={loading} />
    </div>
  );
}


function RankingPanel({
  category,
  transfers,
  loading,
}: {
  category: "best" | "worst";
  transfers: RankedTransfer[];
  loading: boolean;
}) {
  const accent = category === "best" ? "#22c55e" : "#ef4444";
  const heading = category === "best" ? "Best Value Transfers" : "Worst Value Transfers";

  return (
    <section
      className="rounded-xl bg-white/[0.02] border border-white/[0.06] overflow-hidden"
      style={{ borderLeftColor: accent, borderLeftWidth: 3 }}
    >
      <header className="flex items-center justify-between px-4 py-3 border-b border-white/[0.04]">
        <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em]" style={{ color: accent }}>
          {heading}
        </h2>
        <span className="text-[11px] text-[#6b8a78] tabular-nums">{transfers.length} shown</span>
      </header>

      {loading && transfers.length === 0 ? (
        <ul className="divide-y divide-white/[0.03]">
          {Array.from({ length: 10 }).map((_, i) => (
            <li key={i} className="px-4 py-3 animate-pulse">
              <div className="h-3 bg-white/[0.04] rounded w-2/3 mb-2" />
              <div className="h-2.5 bg-white/[0.03] rounded w-1/2" />
            </li>
          ))}
        </ul>
      ) : transfers.length === 0 ? (
        <div className="py-8">
          <EmptyState message="No transfers match the current filters" />
        </div>
      ) : (
        <ol className={`divide-y divide-white/[0.03] ${loading ? "opacity-60 transition-opacity" : ""}`}>
          {transfers.map((t, i) => (
            <RankingRow key={t.transfer_id} rank={i + 1} transfer={t} />
          ))}
        </ol>
      )}
    </section>
  );
}


function RankingRow({ rank, transfer }: { rank: number; transfer: RankedTransfer }) {
  const colors = getGradeColors(transfer.letter_grade);
  return (
    <li className="px-4 py-3 hover:bg-white/[0.025] transition-colors">
      <div className="flex items-center gap-3">
        <span
          className="w-6 shrink-0 text-center text-[15px] font-semibold tabular-nums"
          style={{ color: colors.bg }}
        >
          {rank}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <Link
              to={`/players/${transfer.player_id}`}
              className="text-[13px] font-medium text-[#e8f0ec] hover:text-[#4ade80] transition-colors truncate"
            >
              {transfer.player_name}
            </Link>
            <span className="text-[11px] text-[#6b8a78] truncate">
              {transfer.from_club_name} <span className="text-white/15">→</span> {transfer.to_club_name}
            </span>
          </div>
          <p className="text-[11px] text-[#8fa898] mt-0.5 truncate">{transfer.summary}</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-[12px] font-data tabular-nums text-[#c5dace]">
            {formatFee(transfer.fee_eur)}
          </span>
          <GradeBadge
            letterGrade={transfer.letter_grade}
            compositeScore={transfer.composite_score}
            isComplete={transfer.is_complete}
            size="md"
          />
        </div>
      </div>
    </li>
  );
}
