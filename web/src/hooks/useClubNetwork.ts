import { useEffect, useState } from "react";
import { fetchClubNetwork, fetchClubNetworkExpand } from "@/lib/api";
import type { FilterState } from "@/types/filter";
import type { ClubNetworkResponse, ClubNetworkExpandResponse } from "@/types/api";

interface UseClubNetworkResult {
  networkData: ClubNetworkResponse | null;
  expandedData: Map<number, ClubNetworkExpandResponse>;
  isLoading: boolean;
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

  // Fetch base network on club or filter change
  useEffect(() => {
    if (clubId === null) {
      setNetworkData(null);
      return;
    }
    setIsLoading(true);
    setExpandedCountries(new Set());
    setExpandedData(new Map());

    fetchClubNetwork(clubId, filters)
      .then(setNetworkData)
      .catch(() => setNetworkData(null))
      .finally(() => setIsLoading(false));
  }, [
    clubId,
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

  return { networkData, expandedData, isLoading, expandCountry, collapseCountry, expandedCountries };
}
