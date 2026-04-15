import { memo, useCallback, useEffect, useState } from "react";
import { useFilters } from "@/hooks/useFilters";
import { useDebounce } from "@/hooks/useDebounce";
import { formatFee } from "@/lib/format";
import type { PositionGroup } from "@/types/filter";

const POSITION_GROUPS: { key: PositionGroup; label: string; active: string; inactive: string }[] = [
  { key: "GK", label: "GK", active: "bg-amber-500/20 text-amber-400 border-amber-500/40 shadow-[0_0_8px_rgba(245,158,11,0.15)]", inactive: "text-amber-500/40 border-white/[0.06]" },
  { key: "DEF", label: "DEF", active: "bg-blue-500/20 text-blue-400 border-blue-500/40 shadow-[0_0_8px_rgba(59,130,246,0.15)]", inactive: "text-blue-500/40 border-white/[0.06]" },
  { key: "MID", label: "MID", active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.15)]", inactive: "text-emerald-500/40 border-white/[0.06]" },
  { key: "FWD", label: "FWD", active: "bg-red-500/20 text-red-400 border-red-500/40 shadow-[0_0_8px_rgba(239,68,68,0.15)]", inactive: "text-red-500/40 border-white/[0.06]" },
];

const TRANSFER_TYPES = ["permanent", "loan", "all"] as const;

function abbreviateWindow(w: string): string {
  const match = w.match(/^(Summer|Winter)\s+(\d{4})$/);
  if (!match) return w;
  return `${match[1][0]}${match[2].slice(2)}`;
}

/** Global filter bar with refined glass treatment. */
export const FilterBar = memo(function FilterBar() {
  const { filters, dispatch, availableWindows } = useFilters();

  const [windowRange, setWindowRange] = useState<[number, number]>([0, 0]);
  const [feeRange, setFeeRange] = useState<[number, number]>([0, 100]);
  const [ageRange, setAgeRange] = useState<[number, number]>([15, 40]);

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

  const debouncedWindowRange = useDebounce(windowRange, 300);
  const debouncedFeeRange = useDebounce(feeRange, 300);
  const debouncedAgeRange = useDebounce(ageRange, 300);

  useEffect(() => {
    if (availableWindows.length === 0) return;
    const start = availableWindows[debouncedWindowRange[0]]?.value ?? null;
    const end = availableWindows[debouncedWindowRange[1]]?.value ?? null;
    dispatch({ type: "SET_WINDOW_START", value: start });
    dispatch({ type: "SET_WINDOW_END", value: end });
  }, [debouncedWindowRange, availableWindows, dispatch]);

  const MAX_FEE_EUR = 250_000_000;
  const MAX_FEE_CENTS = MAX_FEE_EUR * 100;

  useEffect(() => {
    const minFee = debouncedFeeRange[0] === 0 ? 0 : Math.round(Math.pow(10, (debouncedFeeRange[0] / 100) * Math.log10(MAX_FEE_CENTS)));
    const maxFee = debouncedFeeRange[1] >= 100 ? null : Math.round(Math.pow(10, (debouncedFeeRange[1] / 100) * Math.log10(MAX_FEE_CENTS)));
    dispatch({ type: "SET_FEE_MIN", value: minFee });
    dispatch({ type: "SET_FEE_MAX", value: maxFee });
  }, [debouncedFeeRange, dispatch]);

  useEffect(() => {
    dispatch({ type: "SET_AGE_MIN", value: debouncedAgeRange[0] <= 15 ? null : debouncedAgeRange[0] });
    dispatch({ type: "SET_AGE_MAX", value: debouncedAgeRange[1] >= 40 ? null : debouncedAgeRange[1] });
  }, [debouncedAgeRange, dispatch]);

  const togglePosition = useCallback((pg: PositionGroup) => {
    const current = filters.positionGroups;
    const next = current.includes(pg)
      ? current.filter((p) => p !== pg)
      : [...current, pg];
    dispatch({ type: "SET_POSITION_GROUPS", value: next.length === 4 ? [] : next });
  }, [filters.positionGroups, dispatch]);

  const windowStartLabel = availableWindows[windowRange[0]]?.value;
  const windowEndLabel = availableWindows[windowRange[1]]?.value;

  const feeMinDisplay = feeRange[0] === 0 ? "€0" : formatFee(Math.round(Math.pow(10, (feeRange[0] / 100) * Math.log10(MAX_FEE_CENTS))));
  const feeMaxDisplay = feeRange[1] >= 100 ? "Max" : formatFee(Math.round(Math.pow(10, (feeRange[1] / 100) * Math.log10(MAX_FEE_CENTS))));

  function FilterLabel({ label, left, right }: { label: string; left?: string; right?: string }) {
    return (
      <div className="flex justify-between items-baseline mb-1">
        <span className="font-data text-[10px] text-[#4ade80]/60 tabular-nums">{left}</span>
        <span className="text-[9px] font-medium uppercase tracking-[0.1em] text-[#6b8a78]">{label}</span>
        <span className="font-data text-[10px] text-[#4ade80]/60 tabular-nums">{right}</span>
      </div>
    );
  }

  return (
    <div className="h-14 bg-[#0e1f16]/60 backdrop-blur-lg border-b border-white/[0.04] flex items-center gap-4 px-5 shrink-0 relative noise">

      {/* Time range */}
      <div className="flex flex-col flex-[2.5] min-w-0">
        <FilterLabel
          label="Window"
          left={windowStartLabel ? abbreviateWindow(windowStartLabel) : ""}
          right={windowEndLabel ? abbreviateWindow(windowEndLabel) : ""}
        />
        <div className="flex gap-1.5 items-center">
          <input
            type="range"
            min={0}
            max={Math.max(availableWindows.length - 1, 0)}
            value={windowRange[0]}
            onChange={(e) => setWindowRange([Math.min(Number(e.target.value), windowRange[1]), windowRange[1]])}
            className="flex-1 h-1"
          />
          <input
            type="range"
            min={0}
            max={Math.max(availableWindows.length - 1, 0)}
            value={windowRange[1]}
            onChange={(e) => setWindowRange([windowRange[0], Math.max(Number(e.target.value), windowRange[0])])}
            className="flex-1 h-1"
          />
        </div>
      </div>

      {/* Separator */}
      <div className="w-px h-7 bg-white/[0.06]" />

      {/* Transfer type */}
      <div className="flex flex-col">
        <span className="text-[9px] font-medium uppercase tracking-[0.1em] text-[#6b8a78] mb-1 text-center">Type</span>
        <div className="flex rounded-lg overflow-hidden border border-white/[0.06] bg-white/[0.02]">
          {TRANSFER_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => dispatch({ type: "SET_TRANSFER_TYPE", value: t })}
              className={`px-2.5 py-1 text-[11px] font-medium capitalize transition-all duration-200 ${
                filters.transferType === t
                  ? "bg-[#4ade80]/15 text-[#4ade80] shadow-[inset_0_0_0_1px_rgba(74,222,128,0.25)]"
                  : "text-[#6b8a78] hover:text-[#c5dace] hover:bg-white/[0.02]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Separator */}
      <div className="w-px h-7 bg-white/[0.06]" />

      {/* Fee range */}
      <div className="flex flex-col flex-1 min-w-0">
        <FilterLabel label="Fee" left={feeMinDisplay} right={feeMaxDisplay} />
        <div className="flex gap-1.5 items-center">
          <input
            type="range"
            min={0}
            max={100}
            value={feeRange[0]}
            onChange={(e) => setFeeRange([Math.min(Number(e.target.value), feeRange[1]), feeRange[1]])}
            className="flex-1 h-1"
          />
          <input
            type="range"
            min={0}
            max={100}
            value={feeRange[1]}
            onChange={(e) => setFeeRange([feeRange[0], Math.max(Number(e.target.value), feeRange[0])])}
            className="flex-1 h-1"
          />
        </div>
      </div>

      {/* Separator */}
      <div className="w-px h-7 bg-white/[0.06]" />

      {/* Position group */}
      <div className="flex flex-col">
        <span className="text-[9px] font-medium uppercase tracking-[0.1em] text-[#6b8a78] mb-1 text-center">Position</span>
        <div className="flex gap-1">
          {POSITION_GROUPS.map((pg) => (
            <button
              key={pg.key}
              onClick={() => togglePosition(pg.key)}
              className={`px-2 py-0.5 text-[11px] font-semibold rounded-md border transition-all duration-200 ${
                filters.positionGroups.includes(pg.key)
                  ? pg.active
                  : pg.inactive + " bg-white/[0.02] hover:bg-white/[0.04]"
              }`}
            >
              {pg.label}
            </button>
          ))}
        </div>
      </div>

      {/* Separator */}
      <div className="w-px h-7 bg-white/[0.06]" />

      {/* Age range */}
      <div className="flex flex-col flex-1 min-w-0">
        <FilterLabel label="Age" left={String(ageRange[0])} right={String(ageRange[1])} />
        <div className="flex gap-1.5 items-center">
          <input
            type="range"
            min={15}
            max={40}
            value={ageRange[0]}
            onChange={(e) => setAgeRange([Math.min(Number(e.target.value), ageRange[1]), ageRange[1]])}
            className="flex-1 h-1"
          />
          <input
            type="range"
            min={15}
            max={40}
            value={ageRange[1]}
            onChange={(e) => setAgeRange([ageRange[0], Math.max(Number(e.target.value), ageRange[0])])}
            className="flex-1 h-1"
          />
        </div>
      </div>
    </div>
  );
});
