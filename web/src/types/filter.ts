/** Position group codes. */
export type PositionGroup = "GK" | "DEF" | "MID" | "FWD";

/** Transfer type filter values. */
export type TransferType = "paid" | "free" | "all";

/** A transfer window option from the API. */
export interface TransferWindow {
  label: string;
  value: string;
}

/** Global filter state shared across all views. */
export interface FilterState {
  windowStart: string | null;
  windowEnd: string | null;
  transferType: TransferType;
  feeMin: number;
  feeMax: number | null;
  positionGroups: PositionGroup[];
  ageMin: number | null;
  ageMax: number | null;
  countryIds: number[];
}
