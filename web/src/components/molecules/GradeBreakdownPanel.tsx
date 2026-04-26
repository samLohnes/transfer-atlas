import { Check, X } from "lucide-react";
import { Spinner } from "@/components/atoms/Spinner";
import { useGradeDetail } from "@/hooks/useGradeDetail";
import { getGradeColors, scoreToLetter } from "@/lib/gradeColors";
import type { ComponentKey } from "@/types/grade";

const COMPONENT_ROWS: { key: ComponentKey; label: string }[] = [
  { key: "minutes", label: "Minutes" },
  { key: "production", label: "Production" },
  { key: "value_trajectory", label: "Value" },
  { key: "financial_return", label: "Financial" },
];

interface GradeBreakdownPanelProps {
  transferId: number;
  /** Compact data already known from the parent — used as the placeholder header while detail loads. */
  letterGrade: string;
  compositeScore: number;
  isComplete: boolean;
  worthTheFee: boolean;
  /** Render only the inner content (no card chrome). Defaults to false. */
  inline?: boolean;
}

/**
 * Persistent grade breakdown panel for the player page transfer table.
 *
 * Shares the `useGradeDetail` cache with `GradeBadgeWithTooltip`, so a hover
 * before clicking-to-expand reuses the already-fetched detail and the panel
 * renders without a fresh round trip.
 */
export function GradeBreakdownPanel({
  transferId,
  letterGrade,
  compositeScore,
  isComplete,
  worthTheFee,
  inline = false,
}: GradeBreakdownPanelProps) {
  const { detail, loading } = useGradeDetail(transferId, true);

  // Prefer fresh detail; fall back to compact props while loading.
  const headerLetter = detail?.letter_grade ?? letterGrade;
  const headerScore = detail?.composite_score ?? compositeScore;
  const overallColor = getGradeColors(headerLetter);

  const wrapperClass = inline
    ? ""
    : "rounded-lg border border-white/[0.06] bg-[#1e3a2a] p-4";

  return (
    <div className={wrapperClass}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-1">
            Transfer Grade
          </p>
          <p className="text-lg font-semibold tabular-nums" style={{ color: overallColor.bg }}>
            {headerLetter}{" "}
            <span className="text-[#8fa898] text-[14px] font-normal">
              ({Math.round(headerScore)}/100)
            </span>
          </p>
        </div>
        <WorthTheFeeBadge worthTheFee={worthTheFee} />
      </div>

      {loading && !detail ? (
        <div className="flex items-center gap-2 py-3 text-[#8fa898] text-[12px]">
          <Spinner size="sm" />
          <span>Loading grade breakdown…</span>
        </div>
      ) : !detail ? (
        <p className="py-3 text-[#8fa898] text-[12px]">
          Detailed breakdown unavailable.
        </p>
      ) : (
        <ul className="space-y-3">
          {COMPONENT_ROWS.map(({ key, label }) => {
            const c = detail.components[key];
            if (!c) return null;
            return <ComponentRow key={key} label={label} score={c.score} explanation={c.explanation} />;
          })}
        </ul>
      )}

      {/* Footer: in-progress note + version + graded_at */}
      {!isComplete && (
        <p className="mt-3 pt-3 border-t border-[#2d4a38] text-[#8fa898] text-[11px]">
          Grade in progress — financial return pending.
        </p>
      )}
      {detail && (
        <p className="mt-3 pt-3 border-t border-[#2d4a38] text-[#6b8a78] text-[10px] tabular-nums">
          Model {detail.model_version} · Graded {formatGradedAt(detail.graded_at)}
        </p>
      )}
    </div>
  );
}


function ComponentRow({
  label,
  score,
  explanation,
}: {
  label: string;
  score: number;
  explanation: string;
}) {
  const letter = scoreToLetter(score);
  const colors = getGradeColors(letter);
  const pct = Math.max(0, Math.min(100, score));
  return (
    <li>
      <div className="flex items-center gap-2 mb-1">
        <span className="w-[80px] shrink-0 text-[12px] text-[#8fa898]">{label}</span>
        <div
          className="flex-1 h-2 rounded-full overflow-hidden"
          style={{ backgroundColor: "#243d2e" }}
        >
          <div
            className="h-full rounded-full transition-[width] duration-300 ease-out"
            style={{ width: `${pct}%`, backgroundColor: colors.bg }}
          />
        </div>
        <span className="w-[42px] shrink-0 text-right text-[12px] tabular-nums text-[#e8f0ec]">
          {Math.round(score)}/100
        </span>
        <span
          className="w-[28px] shrink-0 text-center text-[12px] font-semibold"
          style={{ color: colors.bg }}
        >
          {letter}
        </span>
      </div>
      <p className="ml-[88px] text-[11px] text-[#8fa898] leading-snug">{explanation}</p>
    </li>
  );
}


function WorthTheFeeBadge({ worthTheFee }: { worthTheFee: boolean }) {
  if (worthTheFee) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
        <Check className="h-3 w-3" />
        Worth the fee
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-500/15 border border-red-500/30 px-2 py-0.5 text-[11px] font-medium text-red-400">
      <X className="h-3 w-3" />
      Not worth the fee
    </span>
  );
}


function formatGradedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return iso;
  }
}
