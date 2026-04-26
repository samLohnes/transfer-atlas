import { Link } from "react-router-dom";
import { Plus, X } from "lucide-react";
import { GradeBadge } from "@/components/atoms/GradeBadge";
import { Spinner } from "@/components/atoms/Spinner";
import { ClubSearchBar } from "@/components/molecules/ClubSearchBar";
import { EmptyState } from "@/components/molecules/EmptyState";
import { formatFee } from "@/lib/format";
import { getGradeColors } from "@/lib/gradeColors";
import type { ClubReportCard } from "@/types/grade";
import type { ClubSearchResult } from "@/types/club";
import { ClubGradeTimeline } from "./ClubGradeTimeline";

const MAX_CLUBS = 3;
const CLUB_COLORS = ["#4ade80", "#38bdf8", "#c084fc"];
const GRADE_ORDER: readonly string[] = ["A", "B+", "B", "C+", "C", "D", "F"];

interface ClubReportCardsProps {
  selectedClubs: ClubSearchResult[];
  reportCards: ClubReportCard[];
  loading: boolean;
  onAdd: (club: ClubSearchResult) => void;
  onRemove: (clubId: number) => void;
}

/** Club selector + comparative line chart + per-club stat cards. */
export function ClubReportCards({
  selectedClubs,
  reportCards,
  loading,
  onAdd,
  onRemove,
}: ClubReportCardsProps) {
  const canAddMore = selectedClubs.length < MAX_CLUBS;

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78]">
          Club Report Cards
        </h2>
        <span className="text-[11px] text-[#6b8a78]">{selectedClubs.length} / {MAX_CLUBS}</span>
      </div>

      {/* Selector chips + add */}
      <div className="flex flex-wrap items-center gap-2">
        {selectedClubs.map((c, i) => (
          <span
            key={c.club_id}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/[0.04] border text-[12px] text-[#e8f0ec]"
            style={{ borderColor: CLUB_COLORS[i % CLUB_COLORS.length] + "55" }}
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: CLUB_COLORS[i % CLUB_COLORS.length] }}
            />
            {c.club_name}
            <button
              onClick={() => onRemove(c.club_id)}
              className="text-[#6b8a78] hover:text-[#e8f0ec] transition-colors"
              aria-label={`Remove ${c.club_name}`}
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        {canAddMore && (
          <div className="flex-1 min-w-[240px] max-w-[400px]">
            <ClubSearchBar
              onSelect={onAdd}
              placeholder={selectedClubs.length === 0 ? "Search clubs to compare…" : "Add another club…"}
            />
          </div>
        )}
      </div>

      {/* Body */}
      {selectedClubs.length === 0 ? (
        <div className="py-8">
          <EmptyState message="Search for up to 3 clubs to compare their transfer grades over time." icon={Plus} />
        </div>
      ) : loading && reportCards.length === 0 ? (
        <div className="flex items-center justify-center py-10 gap-3 text-[#8fa898] text-[12px]">
          <Spinner size="sm" />
          <span>Loading club comparison…</span>
        </div>
      ) : (
        <>
          <ClubGradeTimeline clubs={reportCards} />
          <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 ${loading ? "opacity-60 transition-opacity" : ""}`}>
            {reportCards.map((card, i) => (
              <ClubStatCard key={card.club_id} card={card} accent={CLUB_COLORS[i % CLUB_COLORS.length]} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}


function ClubStatCard({ card, accent }: { card: ClubReportCard; accent: string }) {
  const overallColor = getGradeColors(card.overall_letter_grade);
  const maxCount = Math.max(1, ...Object.values(card.grade_distribution));

  return (
    <article
      className="rounded-xl bg-white/[0.02] border border-white/[0.06] overflow-hidden"
      style={{ borderTopColor: accent, borderTopWidth: 3 }}
    >
      <header className="px-4 pt-3 pb-2 border-b border-white/[0.04]">
        <h3 className="text-[14px] font-semibold text-[#e8f0ec] truncate">{card.club_name}</h3>
      </header>

      <div className="px-4 py-3 space-y-3">
        {/* Overall + count */}
        <div className="flex items-end justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.12em] text-[#6b8a78]">Overall</p>
            <p className="text-2xl font-semibold tabular-nums" style={{ color: overallColor.bg }}>
              {card.overall_letter_grade}{" "}
              <span className="text-[#8fa898] text-[14px] font-normal">
                ({Math.round(card.overall_average_grade)})
              </span>
            </p>
          </div>
          <div className="text-right">
            <p className="text-[11px] text-[#8fa898] tabular-nums">{card.total_graded_transfers} transfers</p>
            <p className="text-[12px] text-[#c5dace] font-data tabular-nums">
              {formatFee(card.total_spend_eur)}
            </p>
          </div>
        </div>

        {/* Best / worst */}
        {(card.best_transfer || card.worst_transfer) && (
          <div className="space-y-1.5 pt-2 border-t border-white/[0.04]">
            {card.best_transfer && (
              <BestWorstRow label="Best" t={card.best_transfer} />
            )}
            {card.worst_transfer && (
              <BestWorstRow label="Worst" t={card.worst_transfer} />
            )}
          </div>
        )}

        {/* Distribution bars */}
        <div className="pt-2 border-t border-white/[0.04] space-y-1">
          {GRADE_ORDER.map((grade) => {
            const count = card.grade_distribution[grade] ?? 0;
            const widthPct = (count / maxCount) * 100;
            const colors = getGradeColors(grade);
            return (
              <div key={grade} className="flex items-center gap-2">
                <span
                  className="w-5 text-center text-[11px] font-semibold tabular-nums"
                  style={{ color: colors.bg }}
                >
                  {grade}
                </span>
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ backgroundColor: "#243d2e" }}>
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${widthPct}%`, backgroundColor: colors.bg }}
                  />
                </div>
                <span className="w-6 text-right text-[11px] text-[#8fa898] tabular-nums">{count}</span>
              </div>
            );
          })}
        </div>
      </div>
    </article>
  );
}


function BestWorstRow({
  label,
  t,
}: {
  label: "Best" | "Worst";
  t: NonNullable<ClubReportCard["best_transfer"]>;
}) {
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <span className="w-9 shrink-0 text-[#6b8a78] uppercase tracking-[0.1em] text-[10px] font-semibold">
        {label}
      </span>
      <Link
        to={`/players/${t.player_id}`}
        className="flex-1 text-[#c5dace] truncate hover:text-[#4ade80] transition-colors"
      >
        {t.player_name}
      </Link>
      <GradeBadge
        letterGrade={t.letter_grade}
        compositeScore={t.composite_score}
        isComplete
        size="sm"
      />
      <span className="w-12 text-right text-[#8fa898] font-data tabular-nums">{formatFee(t.fee_eur)}</span>
    </div>
  );
}
