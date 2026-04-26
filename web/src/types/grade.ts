/**
 * Grade-related types.
 *
 * Wire types (matching the FastAPI response shape) keep snake_case to stay
 * consistent with the rest of `web/src/types/`. Component-prop types use
 * camelCase per JS convention; conversion happens at the call site.
 */

// ---------- Wire types (mirror app/schemas/grade.py) -----------------------

export interface GradeBrief {
  composite_score: number;
  letter_grade: string;
  worth_the_fee: boolean;
  is_complete: boolean;
}

export interface GradeComponent {
  score: number;
  explanation: string;
}

export interface GradeDetail {
  transfer_id: number;
  composite_score: number;
  letter_grade: string;
  worth_the_fee: boolean;
  is_complete: boolean;
  components: Partial<Record<ComponentKey, GradeComponent>>;
  model_version: string;
  graded_at: string;
}

export type ComponentKey = "minutes" | "production" | "value_trajectory" | "financial_return";

export interface RankedTransfer {
  transfer_id: number;
  player_name: string;
  player_id: number;
  from_club_name: string;
  to_club_name: string;
  to_club_country: string;
  fee_eur: number;
  composite_score: number;
  letter_grade: string;
  worth_the_fee: boolean;
  is_complete: boolean;
  transfer_window: string;
  position_group: string | null;
  summary: string;
}

export interface TopGradesResponse {
  category: string;
  total: number;
  transfers: RankedTransfer[];
}

export interface ClubBestWorst {
  transfer_id: number;
  player_id: number;
  player_name: string;
  composite_score: number;
  letter_grade: string;
  fee_eur: number;
}

export interface ClubTimeline {
  transfer_window: string;
  average_grade: number;
  transfer_count: number;
}

export interface ClubReportCard {
  club_id: number;
  club_name: string;
  overall_average_grade: number;
  overall_letter_grade: string;
  total_graded_transfers: number;
  total_spend_eur: number;
  best_transfer: ClubBestWorst | null;
  worst_transfer: ClubBestWorst | null;
  grade_distribution: Record<string, number>;
  timeline: ClubTimeline[];
}

export interface ClubComparisonResponse {
  clubs: ClubReportCard[];
}

export interface PlayerGradeSummary {
  average_grade: number;
  total_graded_transfers: number;
  best_grade: ClubBestWorst | null;
  worst_grade: ClubBestWorst | null;
}

export interface ScoringInfoResponse {
  version: string;
  scored_at: string;
  total_scored: number;
  component_weights: Record<string, number>;
  calibrated_rates: Record<string, Record<string, number>>;
  grade_distribution: Record<string, number>;
}

// ---------- Query params for /grades/top -----------------------------------

export interface TopGradesParams {
  category?: "best" | "worst";
  limit?: number;
  offset?: number;
  positionGroup?: string | null;
  countryId?: number | null;
  feeMin?: number | null;
  feeMax?: number | null;
  windowStart?: string | null;
  windowEnd?: string | null;
  completedOnly?: boolean;
}
