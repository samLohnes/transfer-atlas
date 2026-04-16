import { useCallback, useState } from "react";
import { useFilters } from "@/hooks/useFilters";
import { useMapData } from "@/hooks/useMapData";
import { MapView } from "@/components/organisms/MapView";
import { CountryPanel } from "@/components/organisms/CountryPanel";
import { FlowPanel } from "@/components/organisms/FlowPanel";
import { FilterBar } from "@/components/organisms/FilterBar";
import { EmptyState } from "@/components/molecules/EmptyState";
import { ErrorState } from "@/components/molecules/ErrorState";

interface ArcSelection {
  spenderId: number;
  spenderName: string;
  receiverId: number;
  receiverName: string;
}

/** Map view page — the hero view of TransferAtlas. */
export function MapPage() {
  const { filters } = useFilters();
  const { countries, flows, countrySummaries, isLoading, error, retry } = useMapData(filters);
  const [selectedCountryId, setSelectedCountryId] = useState<number | null>(null);
  const [selectedArc, setSelectedArc] = useState<ArcSelection | null>(null);

  const handleSelectCountry = useCallback((id: number | null) => {
    setSelectedCountryId(id);
    setSelectedArc(null);
  }, []);

  const handleSelectArc = useCallback((spenderId: number, receiverId: number, spenderName: string, receiverName: string) => {
    setSelectedArc({ spenderId, spenderName, receiverId, receiverName });
    setSelectedCountryId(null);
  }, []);

  const handleClosePanel = useCallback(() => {
    setSelectedCountryId(null);
    setSelectedArc(null);
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
            onSelectArc={handleSelectArc}
          />
        </div>
      </div>

      {/* Country detail panel (node click) */}
      {selectedCountryId !== null && (
        <CountryPanel countryId={selectedCountryId} onClose={handleClosePanel} />
      )}

      {/* Flow detail panel (arc click) */}
      {selectedArc !== null && (
        <FlowPanel
          countryId={selectedArc.spenderId}
          countryName={selectedArc.spenderName}
          counterpartCountryId={selectedArc.receiverId}
          counterpartCountryName={selectedArc.receiverName}
          onClose={handleClosePanel}
        />
      )}
    </div>
  );
}
