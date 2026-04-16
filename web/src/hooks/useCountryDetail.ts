import { useCallback, useEffect, useState } from "react";
import { fetchCountryDetail } from "@/lib/api";
import type { FilterState } from "@/types/filter";
import type { CountryDetailResponse } from "@/types/api";

interface UseCountryDetailOptions {
  countryId: number | null;
  counterpartCountryId?: number | null;
  direction?: string | null;
  filters: FilterState;
  sortBy: string;
  sortOrder: string;
  page: number;
}

interface UseCountryDetailResult {
  data: CountryDetailResponse | null;
  isLoading: boolean;
  error: string | null;
  retry: () => void;
}

/** Fetches country detail data, re-fetching on any input change. */
export function useCountryDetail({
  countryId,
  counterpartCountryId,
  direction,
  filters,
  sortBy,
  sortOrder,
  page,
}: UseCountryDetailOptions): UseCountryDetailResult {
  const [data, setData] = useState<CountryDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchKey, setFetchKey] = useState(0);

  useEffect(() => {
    if (countryId === null) {
      setData(null);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    fetchCountryDetail(countryId, filters, { sortBy, sortOrder, page, pageSize: 20 }, counterpartCountryId, direction)
      .then(setData)
      .catch((err) => {
        console.error("Failed to fetch country detail:", err);
        setError("Something went wrong loading country data.");
        setData(null);
      })
      .finally(() => setIsLoading(false));
  }, [
    countryId,
    counterpartCountryId,
    direction,
    sortBy,
    sortOrder,
    page,
    fetchKey,
    filters.windowStart,
    filters.windowEnd,
    filters.transferType,
    filters.feeMin,
    filters.feeMax,
    filters.positionGroups?.join(","),
    filters.ageMin,
    filters.ageMax,
  ]);

  const retry = useCallback(() => setFetchKey((k) => k + 1), []);

  return { data, isLoading, error, retry };
}
