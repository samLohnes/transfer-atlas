import { useEffect, useReducer, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { NavBar } from "@/components/organisms/NavBar";
import { MapPage } from "@/components/pages/MapPage";
import { NetworkGraphPage } from "@/components/pages/NetworkGraphPage";
import { PlayerPage } from "@/components/pages/PlayerPage";
import {
  DEFAULT_FILTERS,
  FilterContext,
  filterReducer,
} from "@/hooks/useFilters";
import { fetchWindows, fetchCountries } from "@/lib/api";
import type { TransferWindow } from "@/types/filter";
import type { Country } from "@/types/country";

function App() {
  const [filters, dispatch] = useReducer(filterReducer, DEFAULT_FILTERS);
  const [availableWindows, setAvailableWindows] = useState<TransferWindow[]>([]);
  const [availableCountries, setAvailableCountries] = useState<Country[]>([]);

  useEffect(() => {
    fetchWindows()
      .then((res) => setAvailableWindows(res.windows))
      .catch(() => {});
    fetchCountries()
      .then((res) => setAvailableCountries(res.countries))
      .catch(() => {});
  }, []);

  return (
    <FilterContext value={{ filters, dispatch, availableWindows, availableCountries }}>
      <BrowserRouter>
        <div className="flex flex-col h-screen bg-[#0a1410] text-[#e8f0ec]">
          <NavBar />
          <Routes>
            <Route path="/" element={<MapPage />} />
            <Route path="/network" element={<NetworkGraphPage />} />
            <Route path="/network/:clubId" element={<NetworkGraphPage />} />
            <Route path="/players" element={<PlayerPage />} />
            <Route path="/players/:playerId" element={<PlayerPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </FilterContext>
  );
}

export default App;
