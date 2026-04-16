import { createContext, useContext } from "react";
import type { FilterState, TransferWindow } from "@/types/filter";

/** Actions for the filter reducer. */
export type FilterAction =
  | { type: "SET_WINDOW_START"; value: string | null }
  | { type: "SET_WINDOW_END"; value: string | null }
  | { type: "SET_TRANSFER_TYPE"; value: FilterState["transferType"] }
  | { type: "SET_FEE_MIN"; value: number }
  | { type: "SET_FEE_MAX"; value: number | null }
  | { type: "SET_POSITION_GROUPS"; value: FilterState["positionGroups"] }
  | { type: "SET_AGE_MIN"; value: number | null }
  | { type: "SET_AGE_MAX"; value: number | null }
  | { type: "SET_COUNTRY_IDS"; value: number[] }
  | { type: "TOGGLE_COUNTRY_ID"; value: number }
  | { type: "RESET" };

export const DEFAULT_FILTERS: FilterState = {
  windowStart: null,
  windowEnd: null,
  transferType: "permanent",
  feeMin: 0,
  feeMax: null,
  positionGroups: [],
  ageMin: null,
  ageMax: null,
  countryIds: [],
};

export function filterReducer(state: FilterState, action: FilterAction): FilterState {
  switch (action.type) {
    case "SET_WINDOW_START":
      return { ...state, windowStart: action.value };
    case "SET_WINDOW_END":
      return { ...state, windowEnd: action.value };
    case "SET_TRANSFER_TYPE":
      return { ...state, transferType: action.value };
    case "SET_FEE_MIN":
      return { ...state, feeMin: action.value };
    case "SET_FEE_MAX":
      return { ...state, feeMax: action.value };
    case "SET_POSITION_GROUPS":
      return { ...state, positionGroups: action.value };
    case "SET_AGE_MIN":
      return { ...state, ageMin: action.value };
    case "SET_AGE_MAX":
      return { ...state, ageMax: action.value };
    case "SET_COUNTRY_IDS":
      return { ...state, countryIds: action.value };
    case "TOGGLE_COUNTRY_ID": {
      const current = state.countryIds;
      const next = current.includes(action.value)
        ? current.filter((id) => id !== action.value)
        : [...current, action.value];
      return { ...state, countryIds: next };
    }
    case "RESET":
      return DEFAULT_FILTERS;
    default:
      return state;
  }
}

import type { Country } from "@/types/country";

export interface FilterContextValue {
  filters: FilterState;
  dispatch: React.Dispatch<FilterAction>;
  availableWindows: TransferWindow[];
  availableCountries: Country[];
}

export const FilterContext = createContext<FilterContextValue | null>(null);

/** Access the global filter state from any component. */
export function useFilters(): FilterContextValue {
  const ctx = useContext(FilterContext);
  if (!ctx) throw new Error("useFilters must be used within a FilterProvider");
  return ctx;
}
