import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCountries, fetchCountryFlows } from "@/lib/api";
import type { Country, CountryFlow, CountrySummary } from "@/types/country";
import type { FilterState } from "@/types/filter";

interface MapData {
  countries: Country[];
  flows: CountryFlow[];
  countrySummaries: CountrySummary[];
  isLoading: boolean;
  error: string | null;
  retry: () => void;
}

/** Fetches countries (once) and flows (on filter change) for the map view. */
export function useMapData(filters: FilterState): MapData {
  const [countries, setCountries] = useState<Country[]>([]);
  const [flows, setFlows] = useState<CountryFlow[]>([]);
  const [countrySummaries, setCountrySummaries] = useState<CountrySummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const countriesFetched = useRef(false);
  const [fetchKey, setFetchKey] = useState(0);

  // Fetch countries once
  useEffect(() => {
    if (countriesFetched.current) return;
    countriesFetched.current = true;
    fetchCountries()
      .then((res) => setCountries(res.countries))
      .catch((err) => console.error("Failed to fetch countries:", err));
  }, []);

  // Fetch flows on filter change
  useEffect(() => {
    setIsLoading(true);
    setError(null);
    fetchCountryFlows(filters)
      .then((res) => {
        setFlows(res.flows);
        setCountrySummaries(res.country_summaries);
      })
      .catch((err) => {
        console.error("Failed to fetch flows:", err);
        setError("Something went wrong loading flow data.");
      })
      .finally(() => setIsLoading(false));
  }, [
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

  return { countries, flows, countrySummaries, isLoading, error, retry };
}
