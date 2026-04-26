import { getGradeColors, getIncompleteColors } from "@/lib/gradeColors";

interface GradeBadgeProps {
  letterGrade: string;
  compositeScore: number;
  isComplete: boolean;
  size?: "sm" | "md";
  onClick?: () => void;
  /**
   * When false the badge renders the muted "incomplete / unknown" state with
   * outline-only styling. `letterGrade` and `compositeScore` are ignored.
   */
  hasGrade?: boolean;
}

/**
 * Compact grade pill — letter + numeric score with a tier-appropriate background.
 * Pure presentational atom; the molecule (`GradeBadgeWithTooltip`) layers the
 * hover tooltip and click-to-navigate behaviour on top of this.
 */
export function GradeBadge({
  letterGrade,
  compositeScore,
  isComplete,
  size = "md",
  onClick,
  hasGrade = true,
}: GradeBadgeProps) {
  const incomplete = !hasGrade;
  const colors = incomplete ? getIncompleteColors() : getGradeColors(letterGrade);

  const dimensions =
    size === "sm"
      ? "min-w-[48px] h-5 px-1.5 text-[10px]"
      : "min-w-[60px] h-6 px-2 text-[12px]";

  const interactive = Boolean(onClick) && !incomplete;
  const cursor = interactive ? "cursor-pointer" : "cursor-default";
  const hoverState = interactive ? "hover:brightness-110" : "";

  const baseStyle: React.CSSProperties = {
    backgroundColor: colors.bg,
    color: colors.text,
    border: incomplete ? `1px solid ${colors.border ?? colors.text}` : "none",
  };

  const label = incomplete
    ? size === "md"
      ? "In Progress"
      : "—"
    : `${letterGrade} ${formatScore(compositeScore)}`;

  const ariaLabel = incomplete
    ? "Transfer grade not yet available"
    : `Transfer grade: ${letterGrade}, ${formatScore(compositeScore)} out of 100${isComplete ? "" : ", in progress"}`;

  return (
    <span
      role={interactive ? "button" : "img"}
      aria-label={ariaLabel}
      tabIndex={interactive ? 0 : undefined}
      onClick={interactive ? onClick : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={`inline-flex items-center justify-center rounded font-semibold tabular-nums select-none transition-[filter,background-color] duration-150 ease-out ${dimensions} ${cursor} ${hoverState}`}
      style={baseStyle}
      title={incomplete && !isComplete ? "Grade in progress" : undefined}
    >
      {label}
    </span>
  );
}

/**
 * Round to nearest int for display. Composite scores come back as e.g. 78.5,
 * but the badge label is a single line and benefits from a tight integer.
 */
function formatScore(score: number): number {
  return Math.round(score);
}
