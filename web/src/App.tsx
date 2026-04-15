import { useEffect, useReducer, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { NavBar } from "@/components/organisms/NavBar";
import { MapPage } from "@/components/pages/MapPage";
import { NetworkGraphPage } from "@/components/pages/NetworkGraphPage";
import {
  DEFAULT_FILTERS,
  FilterContext,
  filterReducer,
} from "@/hooks/useFilters";
import { fetchWindows } from "@/lib/api";
import type { TransferWindow } from "@/types/filter";

function App() {
  const [filters, dispatch] = useReducer(filterReducer, DEFAULT_FILTERS);
  const [availableWindows, setAvailableWindows] = useState<TransferWindow[]>([]);

  useEffect(() => {
    fetchWindows()
      .then((res) => setAvailableWindows(res.windows))
      .catch(() => {});
  }, []);

  return (
    <FilterContext value={{ filters, dispatch, availableWindows }}>
      <BrowserRouter>
        <div className="flex flex-col h-screen bg-[#0f1a14] text-[#e8f0ec]">
          <NavBar />
          <Routes>
            <Route path="/" element={<MapPage />} />
            <Route path="/network" element={<NetworkGraphPage />} />
            <Route path="/network/:clubId" element={<NetworkGraphPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </FilterContext>
  );
}

export default App;
