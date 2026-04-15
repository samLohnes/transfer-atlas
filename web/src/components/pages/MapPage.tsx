import { useCallback, useState } from "react";
import { useFilters } from "@/hooks/useFilters";
import { useMapData } from "@/hooks/useMapData";
import { MapView } from "@/components/organisms/MapView";
import { DetailPanel } from "@/components/organisms/DetailPanel";
import { FilterBar } from "@/components/organisms/FilterBar";
import { EmptyState } from "@/components/molecules/EmptyState";
import { ErrorState } from "@/components/molecules/ErrorState";

/** Map view page — the hero view of TransferAtlas. */
export function MapPage() {
  const { filters } = useFilters();
  const { countries, flows, countrySummaries, isLoading, error, retry } = useMapData(filters);
  const [selectedCountryId, setSelectedCountryId] = useState<number | null>(null);

  const handleSelectCountry = useCallback((id: number | null) => {
    setSelectedCountryId(id);
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedCountryId(null);
  }, []);

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex flex-col flex-1 min-w-0">
        <FilterBar />

        <div className="flex-1 relative">
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <ErrorState message={error} onRetry={retry} />
            </div>
          ) : !isLoading && flows.length === 0 && countries.length > 0 ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <EmptyState message="No transfers match your current filters. Try adjusting the time range or removing filters." />
            </div>
          ) : null}

          <MapView
            countries={countries}
            flows={flows}
            countrySummaries={countrySummaries}
            isLoading={isLoading}
            selectedCountryId={selectedCountryId}
            onSelectCountry={handleSelectCountry}
          />
        </div>
      </div>

      <DetailPanel countryId={selectedCountryId} onClose={handleClosePanel} />
    </div>
  );
}
