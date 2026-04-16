import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useFilters } from "@/hooks/useFilters";
import { useClubNetwork } from "@/hooks/useClubNetwork";
import { ClubSearchBar } from "@/components/molecules/ClubSearchBar";
import { NetworkGraph } from "@/components/organisms/NetworkGraph";
import { NetworkDetailPanel } from "@/components/organisms/NetworkDetailPanel";
import type { NetworkDetailPanelProps } from "@/components/organisms/NetworkDetailPanel";
import { FilterBar } from "@/components/organisms/FilterBar";

/** Network graph page — club-centric transfer relationship explorer. */
export function NetworkGraphPage() {
  const { clubId: clubIdParam } = useParams<{ clubId: string }>();
  const { filters } = useFilters();

  const [clubId, setClubId] = useState<number | null>(
    clubIdParam ? parseInt(clubIdParam, 10) : null,
  );

  useEffect(() => {
    setClubId(clubIdParam ? parseInt(clubIdParam, 10) : null);
  }, [clubIdParam]);

  const {
    networkData,
    expandedData,
    expandedCountries,
    isLoading,
    error,
    retry,
    expandCountry,
    collapseCountry,
  } = useClubNetwork(clubId, filters);

  const [selection, setSelection] = useState<NetworkDetailPanelProps["selection"]>(null);

  // Clear selection when club changes
  useEffect(() => { setSelection(null); }, [clubId]);

  const handleSelectCountry = useCallback((countryId: number) => {
    if (!networkData) return;
    const edge = networkData.country_edges.find((e) => e.country_id === countryId);
    if (!edge) return;
    const expanded = expandedData.get(countryId);
    setSelection({
      type: "country",
      countryId,
      countryName: edge.country_name,
      edge,
      expandedData: expanded,
    });
  }, [networkData, expandedData]);

  // Update the country selection when expanded data arrives
  useEffect(() => {
    if (selection?.type !== "country") return;
    const expanded = expandedData.get(selection.countryId);
    if (expanded && !selection.expandedData) {
      setSelection((prev) => prev?.type === "country" ? { ...prev, expandedData: expanded } : prev);
    }
  }, [expandedData, selection]);

  const handleSelectClub = useCallback((clickedClubId: number) => {
    for (const [, expanded] of expandedData) {
      const clubEdge = expanded.club_edges.find((ce) => ce.club_id === clickedClubId);
      if (clubEdge) {
        setSelection({
          type: "club",
          clubId: clickedClubId,
          clubName: clubEdge.club_name,
          clubEdge,
        });
        return;
      }
    }
  }, [expandedData]);

  const handleClosePanel = useCallback(() => {
    setSelection(null);
  }, []);

  const centerClubName = networkData?.center_club.club_name ?? "";
  const isSelectionOpen = selection !== null;

  return (
    <div className="flex-1 flex min-h-0">
      <div className="flex-1 flex flex-col min-h-0 min-w-0">
        <FilterBar />

        <div className="flex justify-center py-3 px-4 shrink-0">
          <ClubSearchBar className="w-full max-w-[480px]" />
        </div>

        <div className="flex-1 min-h-0">
          <NetworkGraph
            networkData={networkData}
            expandedData={expandedData}
            expandedCountries={expandedCountries}
            isLoading={isLoading}
            error={error}
            onRetry={retry}
            onExpandCountry={expandCountry}
            onCollapseCountry={collapseCountry}
            onSelectCountry={handleSelectCountry}
            onSelectClub={handleSelectClub}
          />
        </div>
      </div>

      <NetworkDetailPanel
        centerClubName={centerClubName}
        isOpen={isSelectionOpen}
        selection={selection}
        onClose={handleClosePanel}
      />
    </div>
  );
}
