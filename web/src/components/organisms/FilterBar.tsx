import { memo, useCallback, useEffect, useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { useFilters } from "@/hooks/useFilters";
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

/** Fee breakpoints in EUR — meaningful values for football transfers. */
const FEE_STEPS_EUR = [
  0, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000,
  15_000_000, 20_000_000, 30_000_000, 50_000_000, 75_000_000,
  100_000_000, 150_000_000, 200_000_000, 250_000_000,
];
const FEE_MAX_INDEX = FEE_STEPS_EUR.length; // Index beyond last = "no max"

function feeIndexToEur(index: number): number | null {
  if (index >= FEE_STEPS_EUR.length) return null; // No limit
  return FEE_STEPS_EUR[index];
}

function feeEurToIndex(eur: number | null): number {
  if (eur === null) return FEE_MAX_INDEX;
  // Find the closest step
  for (let i = FEE_STEPS_EUR.length - 1; i >= 0; i--) {
    if (eur >= FEE_STEPS_EUR[i]) return i;
  }
  return 0;
}

function formatFeeLabel(eur: number | null): string {
  if (eur === null) return "Max";
  if (eur === 0) return "€0";
  return formatFee(eur * 100); // formatFee expects cents
}

function abbreviateWindow(w: string): string {
  const match = w.match(/^(Summer|Winter)\s+(\d{4})$/);
  if (!match) return w;
  return `${match[1][0]}${match[2].slice(2)}`;
}

/** Apply button for popovers with sliders. */
function ApplyButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="mt-3 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-[#4ade80]/15 text-[#4ade80] border border-[#4ade80]/25 hover:bg-[#4ade80]/25 transition-all duration-200"
    >
      <Check className="h-3 w-3" />
      Apply
    </button>
  );
}

/** Popover wrapper. */
function FilterPopover({
  label, summary, summaryWidth, isActive, children, isOpen, onToggle, onClose,
}: {
  label: string; summary: string; summaryWidth?: string; isActive: boolean;
  children: React.ReactNode; isOpen: boolean; onToggle: () => void; onClose: () => void;
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
function FeeInput({ value, onChange, isMax }: { value: number | null; onChange: (eur: number | null) => void; isMax?: boolean }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");

  const display = formatFeeLabel(value);

  function commit() {
    setEditing(false);
    const cleaned = text.replace(/[€,\s]/g, "").toLowerCase();
    if (cleaned === "" || cleaned === "max") {
      if (isMax) onChange(null);
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

/** Global filter bar — popovers with Apply buttons for sliders. */
export const FilterBar = memo(function FilterBar() {
  const { filters, dispatch, availableWindows, availableCountries } = useFilters();
  const [openPopover, setOpenPopover] = useState<string | null>(null);

  // --- Local draft state (not dispatched until Apply) ---
  const [draftWindow, setDraftWindow] = useState<[number, number]>([0, 0]);
  const [draftFee, setDraftFee] = useState<[number, number]>([0, FEE_MAX_INDEX]);
  const [draftAge, setDraftAge] = useState<[number, number]>([15, 40]);

  // --- Committed state (what the chips display) ---
  const [committedWindow, setCommittedWindow] = useState<[number, number]>([0, 0]);
  const [committedFee, setCommittedFee] = useState<[number, number]>([0, FEE_MAX_INDEX]);
  const [committedAge, setCommittedAge] = useState<[number, number]>([15, 40]);

  // Initialize window range
  useEffect(() => {
    if (availableWindows.length === 0) return;
    const startIdx = filters.windowStart
      ? availableWindows.findIndex((w) => w.value === filters.windowStart) : 0;
    const endIdx = filters.windowEnd
      ? availableWindows.findIndex((w) => w.value === filters.windowEnd) : availableWindows.length - 1;
    const range: [number, number] = [Math.max(startIdx, 0), Math.max(endIdx, 0)];
    setDraftWindow(range);
    setCommittedWindow(range);
  }, [availableWindows.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reset draft to committed when popover opens
  useEffect(() => {
    if (openPopover === "window") setDraftWindow(committedWindow);
    if (openPopover === "fee") setDraftFee(committedFee);
    if (openPopover === "age") setDraftAge(committedAge);
  }, [openPopover]); // eslint-disable-line react-hooks/exhaustive-deps

  // --- Apply handlers ---
  function applyWindow() {
    setCommittedWindow(draftWindow);
    dispatch({ type: "SET_WINDOW_START", value: availableWindows[draftWindow[0]]?.value ?? null });
    dispatch({ type: "SET_WINDOW_END", value: availableWindows[draftWindow[1]]?.value ?? null });
    setOpenPopover(null);
  }

  function applyFee() {
    setCommittedFee(draftFee);
    const minEur = feeIndexToEur(draftFee[0]);
    const maxEur = feeIndexToEur(draftFee[1]);
    dispatch({ type: "SET_FEE_MIN", value: minEur !== null ? minEur * 100 : 0 });
    dispatch({ type: "SET_FEE_MAX", value: maxEur !== null ? maxEur * 100 : null });
    setOpenPopover(null);
  }

  function applyAge() {
    setCommittedAge(draftAge);
    dispatch({ type: "SET_AGE_MIN", value: draftAge[0] <= 15 ? null : draftAge[0] });
    dispatch({ type: "SET_AGE_MAX", value: draftAge[1] >= 40 ? null : draftAge[1] });
    setOpenPopover(null);
  }

  const togglePosition = useCallback((pg: PositionGroup) => {
    const current = filters.positionGroups;
    const next = current.includes(pg) ? current.filter((p) => p !== pg) : [...current, pg];
    dispatch({ type: "SET_POSITION_GROUPS", value: next.length === 4 ? [] : next });
  }, [filters.positionGroups, dispatch]);

  // --- Chip summaries (from committed state) ---
  const windowStartLabel = availableWindows[committedWindow[0]]?.value;
  const windowEndLabel = availableWindows[committedWindow[1]]?.value;
  const windowSummary = windowStartLabel && windowEndLabel
    ? `${abbreviateWindow(windowStartLabel)}–${abbreviateWindow(windowEndLabel)}` : "All";
  const windowActive = committedWindow[0] > 0 || committedWindow[1] < availableWindows.length - 1;

  const typeSummary = filters.transferType === "permanent" ? "Perm" : filters.transferType === "loan" ? "Loan" : "All";

  const committedFeeMinEur = feeIndexToEur(committedFee[0]);
  const committedFeeMaxEur = feeIndexToEur(committedFee[1]);
  const feeSummary = committedFee[0] === 0 && committedFee[1] >= FEE_MAX_INDEX
    ? "Any"
    : `${formatFeeLabel(committedFeeMinEur)}–${formatFeeLabel(committedFeeMaxEur)}`;
  const feeActive = committedFee[0] > 0 || committedFee[1] < FEE_MAX_INDEX;

  const posSummary = filters.positionGroups.length === 0 ? "All" : filters.positionGroups.join(", ");
  const ageSummary = committedAge[0] <= 15 && committedAge[1] >= 40 ? "Any" : `${committedAge[0]}–${committedAge[1]}`;
  const ageActive = committedAge[0] > 15 || committedAge[1] < 40;

  const countrySummary = filters.countryIds.length === 0
    ? "All"
    : filters.countryIds.length <= 2
      ? filters.countryIds.map((id) => availableCountries.find((c) => c.id === id)?.name ?? "").join(", ")
      : `${filters.countryIds.length} selected`;

  // Draft display values for popover interiors
  const draftWindowStart = availableWindows[draftWindow[0]]?.value;
  const draftWindowEnd = availableWindows[draftWindow[1]]?.value;
  const draftFeeMinEur = feeIndexToEur(draftFee[0]);
  const draftFeeMaxEur = feeIndexToEur(draftFee[1]);

  return (
    <div className="h-12 bg-[#0e1f16]/60 backdrop-blur-lg border-b border-white/[0.04] flex items-center gap-2 px-5 shrink-0 relative z-30 noise">

      {/* Window */}
      <FilterPopover label="Window" summary={windowSummary} isActive={windowActive}
        isOpen={openPopover === "window"} onToggle={() => setOpenPopover(openPopover === "window" ? null : "window")} onClose={() => setOpenPopover(null)}>
        <div className="w-[260px]">
          <div className="flex justify-between items-center mb-3">
            <span className="font-data text-[13px] text-[#e8f0ec] tabular-nums">{draftWindowStart ? abbreviateWindow(draftWindowStart) : ""}</span>
            <span className="text-[#6b8a78] text-[11px]">to</span>
            <span className="font-data text-[13px] text-[#e8f0ec] tabular-nums">{draftWindowEnd ? abbreviateWindow(draftWindowEnd) : ""}</span>
          </div>
          <DualRangeSlider min={0} max={Math.max(availableWindows.length - 1, 0)}
            valueLow={draftWindow[0]} valueHigh={draftWindow[1]}
            onChange={(low, high) => setDraftWindow([low, high])} />
          <ApplyButton onClick={applyWindow} />
        </div>
      </FilterPopover>

      <div className="w-px h-6 bg-white/[0.06] shrink-0" />

      {/* Type (instant, no apply needed) */}
      <FilterPopover label="Type" summary={typeSummary} isActive={filters.transferType !== "permanent"}
        isOpen={openPopover === "type"} onToggle={() => setOpenPopover(openPopover === "type" ? null : "type")} onClose={() => setOpenPopover(null)}>
        <div className="flex flex-col gap-1">
          {TRANSFER_TYPES.map((t) => (
            <button key={t} onClick={() => { dispatch({ type: "SET_TRANSFER_TYPE", value: t }); setOpenPopover(null); }}
              className={`px-3 py-2 rounded-lg text-[13px] font-medium capitalize text-left transition-all duration-200 ${
                filters.transferType === t ? "bg-[#4ade80]/15 text-[#4ade80]" : "text-[#8fa898] hover:bg-white/[0.04] hover:text-[#c5dace]"
              }`}>{t}</button>
          ))}
        </div>
      </FilterPopover>

      <div className="w-px h-6 bg-white/[0.06] shrink-0" />

      {/* Fee */}
      <FilterPopover label="Fee" summary={feeSummary} summaryWidth="w-[100px]" isActive={feeActive}
        isOpen={openPopover === "fee"} onToggle={() => setOpenPopover(openPopover === "fee" ? null : "fee")} onClose={() => setOpenPopover(null)}>
        <div className="w-[280px]">
          <div className="flex justify-between items-center mb-3">
            <FeeInput value={draftFeeMinEur} onChange={(eur) => {
              const idx = eur === null ? 0 : feeEurToIndex(eur);
              setDraftFee([Math.min(idx, draftFee[1]), draftFee[1]]);
            }} />
            <span className="text-[#6b8a78] text-[11px]">to</span>
            <FeeInput value={draftFeeMaxEur} isMax onChange={(eur) => {
              const idx = eur === null ? FEE_MAX_INDEX : feeEurToIndex(eur);
              setDraftFee([draftFee[0], Math.max(idx, draftFee[0])]);
            }} />
          </div>
          <DualRangeSlider min={0} max={FEE_MAX_INDEX}
            valueLow={draftFee[0]} valueHigh={draftFee[1]}
            onChange={(low, high) => setDraftFee([low, high])} />
          <div className="flex justify-between mt-1 text-[9px] text-[#4a6555] font-data">
            <span>€0</span>
            <span>€5M</span>
            <span>€50M</span>
            <span>€250M+</span>
          </div>
          <ApplyButton onClick={applyFee} />
        </div>
      </FilterPopover>

      <div className="w-px h-6 bg-white/[0.06] shrink-0" />

      {/* Position (instant, no apply needed) */}
      <FilterPopover label="Pos" summary={posSummary} isActive={filters.positionGroups.length > 0}
        isOpen={openPopover === "pos"} onToggle={() => setOpenPopover(openPopover === "pos" ? null : "pos")} onClose={() => setOpenPopover(null)}>
        <div className="flex flex-col gap-1.5">
          <div className="text-[11px] text-[#6b8a78] mb-1">Select positions to filter</div>
          <div className="flex gap-1.5">
            {POSITION_GROUPS.map((pg) => (
              <button key={pg.key} onClick={() => togglePosition(pg.key)}
                className={`px-3 py-1.5 text-[12px] font-semibold rounded-lg border transition-all duration-200 ${
                  filters.positionGroups.includes(pg.key) ? pg.active : pg.inactive + " bg-white/[0.02] hover:bg-white/[0.04]"
                }`}>{pg.label}</button>
            ))}
          </div>
          {filters.positionGroups.length > 0 && (
            <button onClick={() => dispatch({ type: "SET_POSITION_GROUPS", value: [] })}
              className="text-[11px] text-[#6b8a78] hover:text-[#c5dace] mt-1 self-start transition-colors">Clear filter</button>
          )}
        </div>
      </FilterPopover>

      <div className="w-px h-6 bg-white/[0.06] shrink-0" />

      {/* Age */}
      <FilterPopover label="Age" summary={ageSummary} isActive={ageActive}
        isOpen={openPopover === "age"} onToggle={() => setOpenPopover(openPopover === "age" ? null : "age")} onClose={() => setOpenPopover(null)}>
        <div>
          <div className="flex justify-between items-center mb-3">
            <span className="font-data text-[14px] text-[#e8f0ec] tabular-nums">{draftAge[0]}</span>
            <span className="text-[#6b8a78] text-[11px]">to</span>
            <span className="font-data text-[14px] text-[#e8f0ec] tabular-nums">{draftAge[1]}</span>
          </div>
          <DualRangeSlider min={15} max={40} valueLow={draftAge[0]} valueHigh={draftAge[1]}
            onChange={(low, high) => setDraftAge([low, high])} />
          <ApplyButton onClick={applyAge} />
        </div>
      </FilterPopover>

      <div className="w-px h-6 bg-white/[0.06] shrink-0" />

      {/* Country (instant, no apply needed) */}
      <FilterPopover label="Country" summary={countrySummary} isActive={filters.countryIds.length > 0}
        isOpen={openPopover === "country"} onToggle={() => setOpenPopover(openPopover === "country" ? null : "country")} onClose={() => setOpenPopover(null)}>
        <div className="max-h-[300px] overflow-y-auto">
          <div className="text-[11px] text-[#6b8a78] mb-2">Show transfers involving:</div>
          <div className="space-y-0.5">
            {availableCountries.map((c) => (
              <button key={c.id} onClick={() => dispatch({ type: "TOGGLE_COUNTRY_ID", value: c.id })}
                className={`w-full text-left px-3 py-1.5 rounded-lg text-[13px] transition-all duration-200 ${
                  filters.countryIds.includes(c.id) ? "bg-[#4ade80]/15 text-[#4ade80]" : "text-[#8fa898] hover:bg-white/[0.04] hover:text-[#c5dace]"
                }`}>{c.name}</button>
            ))}
          </div>
          {filters.countryIds.length > 0 && (
            <button onClick={() => dispatch({ type: "SET_COUNTRY_IDS", value: [] })}
              className="text-[11px] text-[#6b8a78] hover:text-[#c5dace] mt-2 transition-colors">Clear filter</button>
          )}
        </div>
      </FilterPopover>
    </div>
  );
});
