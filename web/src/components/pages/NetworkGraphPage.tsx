import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useFilters } from "@/hooks/useFilters";
import { useClubNetwork } from "@/hooks/useClubNetwork";
import { ClubSearchBar } from "@/components/molecules/ClubSearchBar";
import { NetworkGraph } from "@/components/organisms/NetworkGraph";
import { FilterBar } from "@/components/organisms/FilterBar";

/** Network graph page — club-centric transfer relationship explorer. */
export function NetworkGraphPage() {
  const { clubId: clubIdParam } = useParams<{ clubId: string }>();
  const navigate = useNavigate();
  const { filters } = useFilters();

  const [clubId, setClubId] = useState<number | null>(
    clubIdParam ? parseInt(clubIdParam, 10) : null,
  );

  // Sync URL param to state
  useEffect(() => {
    setClubId(clubIdParam ? parseInt(clubIdParam, 10) : null);
  }, [clubIdParam]);

  const {
    networkData,
    expandedData,
    expandedCountries,
    isLoading,
    expandCountry,
    collapseCountry,
  } = useClubNetwork(clubId, filters);

  const handleRecenter = useCallback((newClubId: number) => {
    navigate(`/network/${newClubId}`);
  }, [navigate]);

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <FilterBar />

      {/* Search bar */}
      <div className="flex justify-center py-3 px-4 shrink-0">
        <ClubSearchBar className="w-full max-w-[480px]" />
      </div>

      {/* Network graph — explicit flex child that fills remaining height */}
      <div className="flex-1 min-h-0">
        <NetworkGraph
          networkData={networkData}
          expandedData={expandedData}
          expandedCountries={expandedCountries}
          isLoading={isLoading}
          onExpandCountry={expandCountry}
          onCollapseCountry={collapseCountry}
          onRecenter={handleRecenter}
        />
      </div>
    </div>
  );
}
