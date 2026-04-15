import { useCallback, useState } from "react";
import { useFilters } from "@/hooks/useFilters";
import { useMapData } from "@/hooks/useMapData";
import { MapView } from "@/components/organisms/MapView";

/** Map view page — the hero view of TransferAtlas. */
export function MapPage() {
  const { filters } = useFilters();
  const { countries, flows, countrySummaries, isLoading } = useMapData(filters);
  const [selectedCountryId, setSelectedCountryId] = useState<number | null>(null);

  const handleSelectCountry = useCallback((id: number | null) => {
    setSelectedCountryId(id);
  }, []);

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex flex-col flex-1">
        {/* Filter bar placeholder — built in Task 9 */}
        <div className="h-14 bg-[#1a2e22] border-b border-[#2d4a38] shrink-0" />

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

      {/* Detail panel slot — built in Task 7 */}
    </div>
  );
}
