import { memo, useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useFilters } from "@/hooks/useFilters";
import { useDebounce } from "@/hooks/useDebounce";
import { formatFee } from "@/lib/format";
import { DualRangeSlider } from "@/components/atoms/DualRangeSlider";
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

/** Popover wrapper — opens below the trigger, closes on outside click. */
function FilterPopover({
  label,
  summary,
  summaryWidth,
  isActive,
  children,
  isOpen,
  onToggle,
  onClose,
}: {
  label: string;
  summary: string;
  summaryWidth?: string;
  isActive: boolean;
  children: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isOpen, onClose]);

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        onClick={onToggle}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-200 border ${
          isOpen
            ? "bg-[#4ade80]/10 text-[#4ade80] border-[#4ade80]/25"
            : isActive
              ? "bg-white/[0.04] text-[#c5dace] border-white/[0.08]"
              : "bg-white/[0.02] text-[#6b8a78] border-white/[0.06] hover:bg-white/[0.04] hover:text-[#c5dace]"
        }`}
      >
        <span className="uppercase tracking-[0.08em] text-[9px] text-[#6b8a78]">{label}</span>
        <span className={`font-data tabular-nums text-center truncate ${summaryWidth ?? "w-[100px]"}`}>{summary}</span>
        <ChevronDown className={`h-3 w-3 text-[#6b8a78] transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 z-50 rounded-xl bg-[#0e1f16]/95 backdrop-blur-xl border border-white/[0.08] shadow-[0_16px_48px_rgba(0,0,0,0.5)] p-4 min-w-[240px] overflow-hidden">
          {children}
        </div>
      )}
    </div>
  );
}

/** Inline editable fee value. */
function FeeInput({ value, onChange, isMax }: { value: number | null; onChange: (eur: number) => void; isMax?: boolean }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");

  const display = value === null ? "Max" : formatFee(value * 100);

  function commit() {
    setEditing(false);
    const cleaned = text.replace(/[€,\s]/g, "").toLowerCase();
    if (cleaned === "" || cleaned === "max") {
      if (isMax) { onChange(0); }
      return;
    }
    let eur = 0;
    if (cleaned.endsWith("m")) {
      eur = parseFloat(cleaned) * 1_000_000;
    } else if (cleaned.endsWith("k")) {
      eur = parseFloat(cleaned) * 1_000;
    } else {
      eur = parseFloat(cleaned);
    }
    if (!isNaN(eur) && eur >= 0) onChange(eur);
  }

  if (editing) {
    return (
      <input
        autoFocus
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") setEditing(false); }}
        placeholder={isMax ? "e.g. 50m" : "e.g. 1m"}
        className="w-20 bg-white/[0.06] border border-[#4ade80]/30 rounded-md px-2 py-1 text-[12px] font-data text-[#e8f0ec] outline-none tabular-nums"
      />
    );
  }

  return (
    <button
      onClick={() => { setEditing(true); setText(""); }}
      className="font-data text-[12px] text-[#4ade80]/70 tabular-nums hover:text-[#4ade80] cursor-text transition-colors px-2 py-1 rounded-md hover:bg-white/[0.04]"
      title="Click to type a value (e.g. 50m, 500k)"
    >
      {display}
    </button>
  );
}

/** Global filter bar — time slider always visible, other filters as popovers. */
export const FilterBar = memo(function FilterBar() {
  const { filters, dispatch, availableWindows, availableCountries } = useFilters();
  const [openPopover, setOpenPopover] = useState<string | null>(null);

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
    dispatch({ type: "SET_WINDOW_START", value: availableWindows[debouncedWindowRange[0]]?.value ?? null });
    dispatch({ type: "SET_WINDOW_END", value: availableWindows[debouncedWindowRange[1]]?.value ?? null });
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
    const next = current.includes(pg) ? current.filter((p) => p !== pg) : [...current, pg];
    dispatch({ type: "SET_POSITION_GROUPS", value: next.length === 4 ? [] : next });
  }, [filters.positionGroups, dispatch]);

  // Summaries for chips
  const typeSummary = filters.transferType === "permanent" ? "Perm" : filters.transferType === "loan" ? "Loan" : "All";
  const feeMinEur = feeRange[0] === 0 ? 0 : Math.round(Math.pow(10, (feeRange[0] / 100) * Math.log10(MAX_FEE_CENTS))) / 100;
  const feeMaxEur = feeRange[1] >= 100 ? null : Math.round(Math.pow(10, (feeRange[1] / 100) * Math.log10(MAX_FEE_CENTS))) / 100;
  const feeSummary = feeRange[0] === 0 && feeRange[1] >= 100
    ? "Any"
    : `${formatFee(feeMinEur * 100)}–${feeMaxEur === null ? "Max" : formatFee(feeMaxEur * 100)}`;
  const posSummary = filters.positionGroups.length === 0 ? "All" : filters.positionGroups.join(", ");
  const ageSummary = ageRange[0] <= 15 && ageRange[1] >= 40 ? "Any" : `${ageRange[0]}–${ageRange[1]}`;
  const countrySummary = filters.countryIds.length === 0
    ? "All"
    : filters.countryIds.length <= 2
      ? filters.countryIds.map((id) => availableCountries.find((c) => c.id === id)?.name ?? "").join(", ")
      : `${filters.countryIds.length} selected`;

  const windowStartLabel = availableWindows[windowRange[0]]?.value;
  const windowEndLabel = availableWindows[windowRange[1]]?.value;

  return (
    <div className="h-12 bg-[#0e1f16]/60 backdrop-blur-lg border-b border-white/[0.04] flex items-center gap-2 px-5 shrink-0 relative z-30 noise">

      {/* Window popover */}
      <FilterPopover
        label="Window"
        summary={windowStartLabel && windowEndLabel
          ? `${abbreviateWindow(windowStartLabel)}–${abbreviateWindow(windowEndLabel)}`
          : "All"}
        isActive={windowRange[0] > 0 || windowRange[1] < availableWindows.length - 1}
        isOpen={openPopover === "window"}
        onToggle={() => setOpenPopover(openPopover === "window" ? null : "window")}
        onClose={() => setOpenPopover(null)}
      >
        <div className="w-[260px]">
          <div className="flex justify-between items-center mb-3">
            <span className="font-data text-[13px] text-[#e8f0ec] tabular-nums">
              {windowStartLabel ? abbreviateWindow(windowStartLabel) : ""}
            </span>
            <span className="text-[#6b8a78] text-[11px]">to</span>
            <span className="font-data text-[13px] text-[#e8f0ec] tabular-nums">
              {windowEndLabel ? abbreviateWindow(windowEndLabel) : ""}
            </span>
          </div>
          <DualRangeSlider
            min={0}
            max={Math.max(availableWindows.length - 1, 0)}
            valueLow={windowRange[0]}
            valueHigh={windowRange[1]}
            onChange={(low, high) => setWindowRange([low, high])}
          />
        </div>
      </FilterPopover>

      {/* Separator */}
      <div className="w-px h-6 bg-white/[0.06] shrink-0" />

      {/* Transfer type popover */}
      <FilterPopover
        label="Type"
        summary={typeSummary}
        isActive={filters.transferType !== "permanent"}
        isOpen={openPopover === "type"}
        onToggle={() => setOpenPopover(openPopover === "type" ? null : "type")}
        onClose={() => setOpenPopover(null)}
      >
        <div className="flex flex-col gap-1">
          {TRANSFER_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => { dispatch({ type: "SET_TRANSFER_TYPE", value: t }); setOpenPopover(null); }}
              className={`px-3 py-2 rounded-lg text-[13px] font-medium capitalize text-left transition-all duration-200 ${
                filters.transferType === t
                  ? "bg-[#4ade80]/15 text-[#4ade80]"
                  : "text-[#8fa898] hover:bg-white/[0.04] hover:text-[#c5dace]"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </FilterPopover>

      {/* Fee popover */}
      <FilterPopover
        label="Fee"
        summary={feeSummary}
        summaryWidth="w-[100px]"
        isActive={feeRange[0] > 0 || feeRange[1] < 100}
        isOpen={openPopover === "fee"}
        onToggle={() => setOpenPopover(openPopover === "fee" ? null : "fee")}
        onClose={() => setOpenPopover(null)}
      >
        <div>
          <div className="flex justify-between items-center mb-4">
            <FeeInput
              value={feeMinEur}
              onChange={(eur) => {
                const v = eur <= 0 ? 0 : Math.round((Math.log10(eur * 100) / Math.log10(MAX_FEE_CENTS)) * 100);
                setFeeRange([Math.min(Math.max(v, 0), feeRange[1]), feeRange[1]]);
              }}
            />
            <span className="text-[#6b8a78] text-[11px]">to</span>
            <FeeInput
              value={feeMaxEur}
              onChange={(eur) => {
                if (eur <= 0) { setFeeRange([feeRange[0], 100]); return; }
                const v = Math.round((Math.log10(eur * 100) / Math.log10(MAX_FEE_CENTS)) * 100);
                setFeeRange([feeRange[0], Math.max(Math.min(v, 100), feeRange[0])]);
              }}
              isMax
            />
          </div>
          <DualRangeSlider
            min={0}
            max={100}
            valueLow={feeRange[0]}
            valueHigh={feeRange[1]}
            onChange={(low, high) => setFeeRange([low, high])}
          />
        </div>
      </FilterPopover>

      {/* Position popover */}
      <FilterPopover
        label="Pos"
        summary={posSummary}
        isActive={filters.positionGroups.length > 0}
        isOpen={openPopover === "pos"}
        onToggle={() => setOpenPopover(openPopover === "pos" ? null : "pos")}
        onClose={() => setOpenPopover(null)}
      >
        <div className="flex flex-col gap-1.5">
          <div className="text-[11px] text-[#6b8a78] mb-1">Select positions to filter</div>
          <div className="flex gap-1.5">
            {POSITION_GROUPS.map((pg) => (
              <button
                key={pg.key}
                onClick={() => togglePosition(pg.key)}
                className={`px-3 py-1.5 text-[12px] font-semibold rounded-lg border transition-all duration-200 ${
                  filters.positionGroups.includes(pg.key)
                    ? pg.active
                    : pg.inactive + " bg-white/[0.02] hover:bg-white/[0.04]"
                }`}
              >
                {pg.label}
              </button>
            ))}
          </div>
          {filters.positionGroups.length > 0 && (
            <button
              onClick={() => dispatch({ type: "SET_POSITION_GROUPS", value: [] })}
              className="text-[11px] text-[#6b8a78] hover:text-[#c5dace] mt-1 self-start transition-colors"
            >
              Clear filter
            </button>
          )}
        </div>
      </FilterPopover>

      {/* Age popover */}
      <FilterPopover
        label="Age"
        summary={ageSummary}
        isActive={ageRange[0] > 15 || ageRange[1] < 40}
        isOpen={openPopover === "age"}
        onToggle={() => setOpenPopover(openPopover === "age" ? null : "age")}
        onClose={() => setOpenPopover(null)}
      >
        <div>
          <div className="flex justify-between items-center mb-4">
            <span className="font-data text-[14px] text-[#e8f0ec] tabular-nums">{ageRange[0]}</span>
            <span className="text-[#6b8a78] text-[11px]">to</span>
            <span className="font-data text-[14px] text-[#e8f0ec] tabular-nums">{ageRange[1]}</span>
          </div>
          <DualRangeSlider
            min={15}
            max={40}
            valueLow={ageRange[0]}
            valueHigh={ageRange[1]}
            onChange={(low, high) => setAgeRange([low, high])}
          />
        </div>
      </FilterPopover>

      {/* Country popover */}
      <FilterPopover
        label="Country"
        summary={countrySummary}
        isActive={filters.countryIds.length > 0}
        isOpen={openPopover === "country"}
        onToggle={() => setOpenPopover(openPopover === "country" ? null : "country")}
        onClose={() => setOpenPopover(null)}
      >
        <div className="max-h-[300px] overflow-y-auto">
          <div className="text-[11px] text-[#6b8a78] mb-2">Show transfers involving:</div>
          <div className="space-y-0.5">
            {availableCountries.map((c) => (
              <button
                key={c.id}
                onClick={() => dispatch({ type: "TOGGLE_COUNTRY_ID", value: c.id })}
                className={`w-full text-left px-3 py-1.5 rounded-lg text-[13px] transition-all duration-200 ${
                  filters.countryIds.includes(c.id)
                    ? "bg-[#4ade80]/15 text-[#4ade80]"
                    : "text-[#8fa898] hover:bg-white/[0.04] hover:text-[#c5dace]"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
          {filters.countryIds.length > 0 && (
            <button
              onClick={() => dispatch({ type: "SET_COUNTRY_IDS", value: [] })}
              className="text-[11px] text-[#6b8a78] hover:text-[#c5dace] mt-2 transition-colors"
            >
              Clear filter
            </button>
          )}
        </div>
      </FilterPopover>
    </div>
  );
});
