import { useEffect, useRef, useState } from "react";
import { fetchCountries, fetchCountryFlows } from "@/lib/api";
import type { Country } from "@/types/country";
import type { CountryFlow, CountrySummary } from "@/types/country";
import type { FilterState } from "@/types/filter";

interface MapData {
  countries: Country[];
  flows: CountryFlow[];
  countrySummaries: CountrySummary[];
  isLoading: boolean;
}

/** Fetches countries (once) and flows (on filter change) for the map view. */
export function useMapData(filters: FilterState): MapData {
  const [countries, setCountries] = useState<Country[]>([]);
  const [flows, setFlows] = useState<CountryFlow[]>([]);
  const [countrySummaries, setCountrySummaries] = useState<CountrySummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const countriesFetched = useRef(false);

  // Fetch countries once
  useEffect(() => {
    if (countriesFetched.current) return;
    countriesFetched.current = true;
    fetchCountries()
      .then((res) => setCountries(res.countries))
      .catch(() => {});
  }, []);

  // Fetch flows on filter change
  useEffect(() => {
    setIsLoading(true);
    fetchCountryFlows(filters)
      .then((res) => {
        setFlows(res.flows);
        setCountrySummaries(res.country_summaries);
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [
    filters.windowStart,
    filters.windowEnd,
    filters.transferType,
    filters.feeMin,
    filters.feeMax,
    filters.positionGroups?.join(","),
    filters.ageMin,
    filters.ageMax,
  ]);

  return { countries, flows, countrySummaries, isLoading };
}
