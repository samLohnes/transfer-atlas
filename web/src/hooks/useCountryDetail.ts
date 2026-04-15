import { useEffect, useState } from "react";
import { fetchCountryDetail } from "@/lib/api";
import type { FilterState } from "@/types/filter";
import type { CountryDetailResponse } from "@/types/api";

interface UseCountryDetailOptions {
  countryId: number | null;
  filters: FilterState;
  sortBy: string;
  sortOrder: string;
  page: number;
}

interface UseCountryDetailResult {
  data: CountryDetailResponse | null;
  isLoading: boolean;
}

/** Fetches country detail data, re-fetching on any input change. */
export function useCountryDetail({
  countryId,
  filters,
  sortBy,
  sortOrder,
  page,
}: UseCountryDetailOptions): UseCountryDetailResult {
  const [data, setData] = useState<CountryDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (countryId === null) {
      setData(null);
      return;
    }

    setIsLoading(true);
    fetchCountryDetail(countryId, filters, { sortBy, sortOrder, page, pageSize: 20 })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setIsLoading(false));
  }, [
    countryId,
    sortBy,
    sortOrder,
    page,
    filters.windowStart,
    filters.windowEnd,
    filters.transferType,
    filters.feeMin,
    filters.feeMax,
    filters.positionGroups?.join(","),
    filters.ageMin,
    filters.ageMax,
  ]);

  return { data, isLoading };
}
