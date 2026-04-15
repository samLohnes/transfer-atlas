import { memo, useCallback, useEffect, useMemo, useState } from "react";
import { useFilters } from "@/hooks/useFilters";
import { useDebounce } from "@/hooks/useDebounce";
import { formatFee } from "@/lib/format";
import type { PositionGroup } from "@/types/filter";

const POSITION_GROUPS: { key: PositionGroup; label: string; color: string; activeColor: string }[] = [
  { key: "GK", label: "GK", color: "border-amber-500/50 text-amber-500", activeColor: "bg-amber-500 text-white border-amber-500" },
  { key: "DEF", label: "DEF", color: "border-blue-500/50 text-blue-500", activeColor: "bg-blue-500 text-white border-blue-500" },
  { key: "MID", label: "MID", color: "border-green-500/50 text-green-500", activeColor: "bg-green-500 text-white border-green-500" },
  { key: "FWD", label: "FWD", color: "border-red-500/50 text-red-500", activeColor: "bg-red-500 text-white border-red-500" },
];

const TRANSFER_TYPES = ["permanent", "loan", "all"] as const;

/** Abbreviate window label: "Summer 2019" → "S19", "Winter 2023" → "W23" */
function abbreviateWindow(w: string): string {
  const match = w.match(/^(Summer|Winter)\s+(\d{4})$/);
  if (!match) return w;
  return `${match[1][0]}${match[2].slice(2)}`;
}

/** Global filter bar rendered above both Map and Network views. */
export const FilterBar = memo(function FilterBar() {
  const { filters, dispatch, availableWindows } = useFilters();

  // Local slider state for responsive UI (debounced before dispatch)
  const [windowRange, setWindowRange] = useState<[number, number]>([0, 0]);
  const [feeRange, setFeeRange] = useState<[number, number]>([0, 100]);
  const [ageRange, setAgeRange] = useState<[number, number]>([15, 40]);

  // Initialize window range from available windows
  useEffect(() => {
    if (availableWindows.length === 0) return;
    const startIdx = filters.windowStart
      ? availableWindows.findIndex((w) => w.value === filters.windowStart)
      : 0;
    const endIdx = filters.windowEnd
      ? availableWindows.findIndex((w) => w.value === filters.windowEnd)
      : availableWindows.length - 1;
    setWindowRange([Math.max(startIdx, 0), Math.max(endIdx, 0)]);
  }, [availableWindows.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced values
  const debouncedWindowRange = useDebounce(windowRange, 300);
  const debouncedFeeRange = useDebounce(feeRange, 300);
  const debouncedAgeRange = useDebounce(ageRange, 300);

  // Dispatch debounced window range
  useEffect(() => {
    if (availableWindows.length === 0) return;
    const start = availableWindows[debouncedWindowRange[0]]?.value ?? null;
    const end = availableWindows[debouncedWindowRange[1]]?.value ?? null;
    dispatch({ type: "SET_WINDOW_START", value: start });
    dispatch({ type: "SET_WINDOW_END", value: end });
  }, [debouncedWindowRange, availableWindows, dispatch]);

  // Dispatch debounced fee range (logarithmic: slider 0-100 → fee in cents)
  const MAX_FEE_EUR = 250_000_000; // €250M
  const MAX_FEE_CENTS = MAX_FEE_EUR * 100;

  useEffect(() => {
    const minFee = debouncedFeeRange[0] === 0 ? 0 : Math.round(Math.pow(10, (debouncedFeeRange[0] / 100) * Math.log10(MAX_FEE_CENTS)));
    const maxFee = debouncedFeeRange[1] >= 100 ? null : Math.round(Math.pow(10, (debouncedFeeRange[1] / 100) * Math.log10(MAX_FEE_CENTS)));
    dispatch({ type: "SET_FEE_MIN", value: minFee });
    dispatch({ type: "SET_FEE_MAX", value: maxFee });
  }, [debouncedFeeRange, dispatch]);

  // Dispatch debounced age range
  useEffect(() => {
    dispatch({ type: "SET_AGE_MIN", value: debouncedAgeRange[0] <= 15 ? null : debouncedAgeRange[0] });
    dispatch({ type: "SET_AGE_MAX", value: debouncedAgeRange[1] >= 40 ? null : debouncedAgeRange[1] });
  }, [debouncedAgeRange, dispatch]);

  // Position group toggle
  const togglePosition = useCallback((pg: PositionGroup) => {
    const current = filters.positionGroups;
    const next = current.includes(pg)
      ? current.filter((p) => p !== pg)
      : [...current, pg];
    // All 4 selected = no filter
    dispatch({ type: "SET_POSITION_GROUPS", value: next.length === 4 ? [] : next });
  }, [filters.positionGroups, dispatch]);

  // Display values
  const windowStartLabel = availableWindows[windowRange[0]]?.value;
  const windowEndLabel = availableWindows[windowRange[1]]?.value;

  const feeMinDisplay = feeRange[0] === 0 ? "€0" : formatFee(Math.round(Math.pow(10, (feeRange[0] / 100) * Math.log10(MAX_FEE_CENTS))));
  const feeMaxDisplay = feeRange[1] >= 100 ? "Max" : formatFee(Math.round(Math.pow(10, (feeRange[1] / 100) * Math.log10(MAX_FEE_CENTS))));

  return (
    <div className="h-14 bg-[#1a2e22] border-b border-[#2d4a38] flex items-center gap-5 px-4 shrink-0">

      {/* Time range slider */}
      <div className="flex flex-col flex-[2] min-w-0">
        <div className="flex justify-between text-[10px] text-[#8fa898] mb-0.5">
          <span>{windowStartLabel ? abbreviateWindow(windowStartLabel) : ""}</span>
          <span className="text-[#8fa898]">Window</span>
          <span>{windowEndLabel ? abbreviateWindow(windowEndLabel) : ""}</span>
        </div>
        <div className="flex gap-1 items-center">
          <input
            type="range"
            min={0}
            max={Math.max(availableWindows.length - 1, 0)}
            value={windowRange[0]}
            onChange={(e) => setWindowRange([Math.min(Number(e.target.value), windowRange[1]), windowRange[1]])}
            className="flex-1 accent-[#4ade80] h-1"
          />
          <input
            type="range"
            min={0}
            max={Math.max(availableWindows.length - 1, 0)}
            value={windowRange[1]}
            onChange={(e) => setWindowRange([windowRange[0], Math.max(Number(e.target.value), windowRange[0])])}
            className="flex-1 accent-[#4ade80] h-1"
          />
        </div>
      </div>

      {/* Transfer type toggle */}
      <div className="flex flex-col">
        <span className="text-[10px] text-[#8fa898] mb-0.5 text-center">Type</span>
        <div className="flex rounded-md overflow-hidden border border-[#2d4a38]">
          {TRANSFER_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => dispatch({ type: "SET_TRANSFER_TYPE", value: t })}
              className={`px-2 py-0.5 text-xs capitalize transition-colors ${
                filters.transferType === t
                  ? "bg-[#4ade80] text-[#0f1a14] font-medium"
                  : "bg-[#243d2e] text-[#8fa898] hover:text-[#e8f0ec]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Fee range slider */}
      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex justify-between text-[10px] text-[#8fa898] mb-0.5">
          <span>{feeMinDisplay}</span>
          <span>Fee</span>
          <span>{feeMaxDisplay}</span>
        </div>
        <div className="flex gap-1 items-center">
          <input
            type="range"
            min={0}
            max={100}
            value={feeRange[0]}
            onChange={(e) => setFeeRange([Math.min(Number(e.target.value), feeRange[1]), feeRange[1]])}
            className="flex-1 accent-[#4ade80] h-1"
          />
          <input
            type="range"
            min={0}
            max={100}
            value={feeRange[1]}
            onChange={(e) => setFeeRange([feeRange[0], Math.max(Number(e.target.value), feeRange[0])])}
            className="flex-1 accent-[#4ade80] h-1"
          />
        </div>
      </div>

      {/* Position group selector */}
      <div className="flex flex-col">
        <span className="text-[10px] text-[#8fa898] mb-0.5 text-center">Position</span>
        <div className="flex gap-0.5">
          {POSITION_GROUPS.map((pg) => {
            const isActive = filters.positionGroups.includes(pg.key) || filters.positionGroups.length === 0;
            return (
              <button
                key={pg.key}
                onClick={() => togglePosition(pg.key)}
                className={`px-1.5 py-0.5 text-xs font-medium rounded border transition-colors ${
                  filters.positionGroups.includes(pg.key)
                    ? pg.activeColor
                    : filters.positionGroups.length === 0
                      ? `border-[#2d4a38] text-[#8fa898] hover:${pg.color}`
                      : `border-[#2d4a38] text-[#4a5a50] hover:${pg.color}`
                }`}
              >
                {pg.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Age range slider */}
      <div className="flex flex-col flex-1 min-w-0">
        <div className="flex justify-between text-[10px] text-[#8fa898] mb-0.5">
          <span>{ageRange[0]}</span>
          <span>Age</span>
          <span>{ageRange[1]}</span>
        </div>
        <div className="flex gap-1 items-center">
          <input
            type="range"
            min={15}
            max={40}
            value={ageRange[0]}
            onChange={(e) => setAgeRange([Math.min(Number(e.target.value), ageRange[1]), ageRange[1]])}
            className="flex-1 accent-[#4ade80] h-1"
          />
          <input
            type="range"
            min={15}
            max={40}
            value={ageRange[1]}
            onChange={(e) => setAgeRange([ageRange[0], Math.max(Number(e.target.value), ageRange[0])])}
            className="flex-1 accent-[#4ade80] h-1"
          />
        </div>
      </div>
    </div>
  );
});
