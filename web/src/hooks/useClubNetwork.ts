import { useCallback, useEffect, useState } from "react";
import { fetchClubNetwork, fetchClubNetworkExpand } from "@/lib/api";
import type { FilterState } from "@/types/filter";
import type { ClubNetworkResponse, ClubNetworkExpandResponse } from "@/types/api";

interface UseClubNetworkResult {
  networkData: ClubNetworkResponse | null;
  expandedData: Map<number, ClubNetworkExpandResponse>;
  isLoading: boolean;
  error: string | null;
  retry: () => void;
  expandCountry: (countryId: number) => void;
  collapseCountry: (countryId: number) => void;
  expandedCountries: Set<number>;
}

/** Manages club network data with country expansion state. */
export function useClubNetwork(clubId: number | null, filters: FilterState): UseClubNetworkResult {
  const [networkData, setNetworkData] = useState<ClubNetworkResponse | null>(null);
  const [expandedData, setExpandedData] = useState<Map<number, ClubNetworkExpandResponse>>(new Map());
  const [expandedCountries, setExpandedCountries] = useState<Set<number>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchKey, setFetchKey] = useState(0);

  useEffect(() => {
    if (clubId === null) {
      setNetworkData(null);
      setError(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    setExpandedCountries(new Set());
    setExpandedData(new Map());

    fetchClubNetwork(clubId, filters)
      .then(setNetworkData)
      .catch((err) => {
        console.error("Failed to fetch club network:", err);
        setError("Something went wrong loading network data.");
        setNetworkData(null);
      })
      .finally(() => setIsLoading(false));
  }, [
    clubId,
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

  function expandCountry(countryId: number) {
    if (clubId === null) return;
    if (expandedCountries.has(countryId)) return;

    fetchClubNetworkExpand(clubId, countryId, filters).then((data) => {
      setExpandedData((prev) => new Map(prev).set(countryId, data));
      setExpandedCountries((prev) => new Set(prev).add(countryId));
    });
  }

  function collapseCountry(countryId: number) {
    setExpandedCountries((prev) => {
      const next = new Set(prev);
      next.delete(countryId);
      return next;
    });
    setExpandedData((prev) => {
      const next = new Map(prev);
      next.delete(countryId);
      return next;
    });
  }

  const retry = useCallback(() => setFetchKey((k) => k + 1), []);

  return { networkData, expandedData, isLoading, error, retry, expandCountry, collapseCountry, expandedCountries };
}
