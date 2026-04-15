import { useCallback, useState } from "react";
import { useFilters } from "@/hooks/useFilters";
import { useMapData } from "@/hooks/useMapData";
import { MapView } from "@/components/organisms/MapView";
import { DetailPanel } from "@/components/organisms/DetailPanel";
import { FilterBar } from "@/components/organisms/FilterBar";

/** Map view page — the hero view of TransferAtlas. */
export function MapPage() {
  const { filters } = useFilters();
  const { countries, flows, countrySummaries, isLoading } = useMapData(filters);
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

        {/* Map */}
        <div className="flex-1 relative">
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

      {/* Detail panel */}
      <DetailPanel countryId={selectedCountryId} onClose={handleClosePanel} />
    </div>
  );
}
