/**
 * Grade-tier color lookup + helpers.
 *
 * Centralized so both `GradeBadge` and `GradeTooltip` reference the same
 * palette. Mirrors the spec's color table from plans/phase2/main.md.
 */

export interface GradeColors {
  bg: string;
  text: string;
  /** Border colour for the muted "incomplete" state — only used when `bg` is transparent. */
  border?: string;
}

const GRADE_COLORS: Record<string, GradeColors> = {
  A: { bg: "#22c55e", text: "#0f1a14" },
  "B+": { bg: "#14b8a6", text: "#0f1a14" },
  B: { bg: "#2dd4bf", text: "#0f1a14" },
  "C+": { bg: "#f59e0b", text: "#0f1a14" },
  C: { bg: "#fbbf24", text: "#0f1a14" },
  D: { bg: "#f97316", text: "#0f1a14" },
  F: { bg: "#ef4444", text: "#ffffff" },
};

const INCOMPLETE_COLORS: GradeColors = {
  bg: "transparent",
  text: "#6b7280",
  border: "#6b7280",
};

/** Returns colors for a letter grade. Falls back to `F` styling for unknown values. */
export function getGradeColors(letterGrade: string): GradeColors {
  return GRADE_COLORS[letterGrade] ?? GRADE_COLORS.F;
}

/** Outline-only "in progress" / unknown styling (no fill). */
export function getIncompleteColors(): GradeColors {
  return INCOMPLETE_COLORS;
}

/**
 * Convert a 0-100 composite score into a letter grade. Mirrors the boundaries
 * in `api/ml/utils.py` so the front-end can render a grade band even when the
 * server hasn't yet sent the explicit letter.
 */
export function scoreToLetter(compositeScore: number): string {
  if (compositeScore >= 85) return "A";
  if (compositeScore >= 78) return "B+";
  if (compositeScore >= 70) return "B";
  if (compositeScore >= 62) return "C+";
  if (compositeScore >= 55) return "C";
  if (compositeScore >= 40) return "D";
  return "F";
}
