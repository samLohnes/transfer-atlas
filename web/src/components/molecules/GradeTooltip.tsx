import { createPortal } from "react-dom";
import { Spinner } from "@/components/atoms/Spinner";
import { getGradeColors, scoreToLetter } from "@/lib/gradeColors";
import type { ComponentKey, GradeComponent } from "@/types/grade";

const COMPONENT_ROWS: { key: ComponentKey; label: string }[] = [
  { key: "minutes", label: "Minutes" },
  { key: "production", label: "Production" },
  { key: "value_trajectory", label: "Value" },
  { key: "financial_return", label: "Financial" },
];

interface GradeTooltipProps {
  /** Pixel offset relative to the viewport. */
  position: { top: number; left: number };
  compositeScore: number;
  letterGrade: string;
  isComplete: boolean;
  components: Partial<Record<ComponentKey, GradeComponent>>;
  modelVersion: string | null;
  loading?: boolean;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

/**
 * Hover tooltip that shows the per-component breakdown for a transfer grade.
 * Rendered via a portal into `#tooltip-root` so z-index stacking contexts
 * elsewhere in the tree can't clip it.
 */
export function GradeTooltip({
  position,
  compositeScore,
  letterGrade,
  isComplete,
  components,
  modelVersion,
  loading = false,
  onMouseEnter,
  onMouseLeave,
}: GradeTooltipProps) {
  const root = document.getElementById("tooltip-root");
  if (!root) return null;

  const overall = getGradeColors(letterGrade);

  return createPortal(
    <div
      role="tooltip"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className="fixed z-[9999] max-w-[380px] min-w-[300px] rounded-lg border bg-[#1e3a2a] px-4 py-3 text-[13px] text-[#e8f0ec] shadow-[0_4px_12px_rgba(0,0,0,0.3)]"
      style={{
        top: position.top,
        left: position.left,
        borderColor: "#2d4a38",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between text-[15px] font-semibold pb-2 mb-2 border-b border-[#2d4a38]">
        <span className="text-[#e8f0ec]">Overall</span>
        <span style={{ color: overall.bg }}>
          {letterGrade} <span className="text-[#8fa898] text-[13px] font-normal ml-1">({Math.round(compositeScore)}/100)</span>
        </span>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-1.5 text-[#8fa898]">
          <Spinner size="sm" />
          <span>Loading grade details…</span>
        </div>
      ) : (
        <ul className="space-y-1.5">
          {COMPONENT_ROWS.map(({ key, label }) => {
            const c = components[key];
            if (!c) return null;
            const componentLetter = scoreToLetter(c.score);
            const componentColor = getGradeColors(componentLetter);
            return (
              <li key={key} className="flex items-center gap-2">
                <span className="w-[80px] shrink-0 text-[#8fa898]">{label}:</span>
                <span
                  className="w-[28px] shrink-0 text-center font-semibold"
                  style={{ color: componentColor.bg }}
                >
                  {componentLetter}
                </span>
                <span className="w-[40px] shrink-0 text-[#e8f0ec] tabular-nums">
                  ({Math.round(c.score)})
                </span>
                <span className="flex-1 truncate text-[#8fa898]">{c.explanation}</span>
              </li>
            );
          })}
        </ul>
      )}

      {/* In-progress note */}
      {!isComplete && !loading && (
        <p className="mt-2 pt-2 border-t border-[#2d4a38] text-[#8fa898] text-[12px]">
          Grade in progress — financial return pending.
        </p>
      )}

      {modelVersion && !loading && (
        <p className="mt-2 pt-2 border-t border-[#2d4a38] text-[#6b8a78] text-[11px] tabular-nums">
          Model {modelVersion}
        </p>
      )}
    </div>,
    root,
  );
}
