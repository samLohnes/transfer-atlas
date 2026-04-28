import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ClipboardList } from "lucide-react";
import { GradeRankings } from "@/components/organisms/GradeRankings";
import { ClubReportCards } from "@/components/organisms/ClubReportCards";
import { EmptyState } from "@/components/molecules/EmptyState";
import { useDebounce } from "@/hooks/useDebounce";
import { useFilters } from "@/hooks/useFilters";
import { fetchClubComparison, fetchTopGrades } from "@/lib/api";
import { FEE_STEPS_EUR } from "@/lib/feeSteps";
import { formatFee } from "@/lib/format";
import type {
  ClubReportCard,
  RankedTransfer,
  TopGradesParams,
} from "@/types/grade";
import type { ClubSearchResult } from "@/types/club";

const POSITION_OPTIONS = [
  { value: "", label: "All positions" },
  { value: "GK", label: "Goalkeeper" },
  { value: "DEF", label: "Defender" },
  { value: "MID", label: "Midfielder" },
  { value: "FWD", label: "Forward" },
];

interface LocalFilters {
  positionGroup: string | null;
  countryId: number | null;
  windowStart: string | null;
  windowEnd: string | null;
  completedOnly: boolean;
  feeMin: number | null;  // EUR cents (or null = no min)
  feeMax: number | null;  // EUR cents (or null = no max)
}

// Options share the FEE_STEPS_EUR list (in EUR) but emit cents in the value
// because TopGradesParams is in EUR cents (matches Transfer.fee_eur storage).
const FEE_OPTIONS_FOR_MIN = [
  { value: "", label: "Any" },
  ...FEE_STEPS_EUR.map((eur) => ({
    value: String(eur * 100),
    label: formatFee(eur * 100),
  })),
];

const FEE_OPTIONS_FOR_MAX = [
  ...FEE_STEPS_EUR.map((eur) => ({
    value: String(eur * 100),
    label: formatFee(eur * 100),
  })),
  { value: "", label: "No max" },
];

const RANKING_LIMIT = 10;

/** Best/worst transfer rankings + comparative club report cards. */
export function GradesPage() {
  const { availableWindows, availableCountries } = useFilters();

  const defaultStart = useMemo(() => {
    if (availableWindows.length === 0) return null;
    // Pick the window ~10 entries from the latest as a "last 5 years"-ish default.
    // availableWindows comes back chronologically ordered (descending — newest first
    // per the existing FilterBar convention), so the higher index is older.
    const idx = Math.min(availableWindows.length - 1, 9);
    return availableWindows[idx]?.value ?? null;
  }, [availableWindows]);

  const [filters, setFilters] = useState<LocalFilters>(() => ({
    positionGroup: null,
    countryId: null,
    windowStart: null,
    windowEnd: null,
    completedOnly: true,
    feeMin: null,
    feeMax: null,
  }));

  // Apply the default window once availableWindows arrives — only if the user
  // hasn't yet touched the start window themselves.
  const hasInitializedWindow = useRef(false);
  useEffect(() => {
    if (!hasInitializedWindow.current && defaultStart) {
      setFilters((prev) => ({ ...prev, windowStart: defaultStart }));
      hasInitializedWindow.current = true;
    }
  }, [defaultStart]);

  const debounced = useDebounce(filters, 300);

  // ---- Rankings data fetch ----
  const [best, setBest] = useState<RankedTransfer[]>([]);
  const [worst, setWorst] = useState<RankedTransfer[]>([]);
  const [rankingsLoading, setRankingsLoading] = useState(false);

  useEffect(() => {
    const params: TopGradesParams = {
      limit: RANKING_LIMIT,
      completedOnly: debounced.completedOnly,
      positionGroup: debounced.positionGroup,
      countryId: debounced.countryId,
      windowStart: debounced.windowStart,
      windowEnd: debounced.windowEnd,
      feeMin: debounced.feeMin,
      feeMax: debounced.feeMax,
    };
    let cancelled = false;
    setRankingsLoading(true);
    Promise.all([
      fetchTopGrades({ ...params, category: "best" }),
      fetchTopGrades({ ...params, category: "worst" }),
    ])
      .then(([b, w]) => {
        if (cancelled) return;
        setBest(b.transfers);
        setWorst(w.transfers);
      })
      .catch((e) => {
        if (cancelled) return;
        console.error("Failed to fetch grade rankings", e);
        setBest([]);
        setWorst([]);
      })
      .finally(() => {
        if (!cancelled) setRankingsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  // ---- Club report card state + fetch ----
  const [selectedClubs, setSelectedClubs] = useState<ClubSearchResult[]>([]);
  const [reportCards, setReportCards] = useState<ClubReportCard[]>([]);
  const [comparisonLoading, setComparisonLoading] = useState(false);

  useEffect(() => {
    if (selectedClubs.length === 0) {
      setReportCards([]);
      return;
    }
    let cancelled = false;
    setComparisonLoading(true);
    fetchClubComparison(
      selectedClubs.map((c) => c.club_id),
      debounced.windowStart,
      debounced.windowEnd,
    )
      .then((res) => {
        if (!cancelled) setReportCards(res.clubs);
      })
      .catch((e) => {
        if (cancelled) return;
        console.error("Failed to fetch club comparison", e);
        setReportCards([]);
      })
      .finally(() => {
        if (!cancelled) setComparisonLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedClubs, debounced.windowStart, debounced.windowEnd]);

  const handleAddClub = useCallback((club: ClubSearchResult) => {
    setSelectedClubs((prev) =>
      prev.some((c) => c.club_id === club.club_id) ? prev : [...prev, club],
    );
  }, []);

  const handleRemoveClub = useCallback((clubId: number) => {
    setSelectedClubs((prev) => prev.filter((c) => c.club_id !== clubId));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[1200px] mx-auto w-full px-6 py-6 space-y-6">
        <header>
          <h1 className="text-[20px] font-semibold text-[#e8f0ec] tracking-tight mb-1">Transfer Grades</h1>
          <p className="text-[13px] text-[#8fa898]">
            Best- and worst-graded transfers across the dataset, plus club-level comparisons.
          </p>
        </header>

        {/* Local filter bar */}
        <div className="flex flex-wrap items-center gap-2 rounded-xl bg-white/[0.02] border border-white/[0.06] px-4 py-3">
          <FilterDropdown
            label="Position"
            value={filters.positionGroup ?? ""}
            onChange={(v) => setFilters((p) => ({ ...p, positionGroup: v || null }))}
            options={POSITION_OPTIONS}
          />
          <FilterDropdown
            label="Country"
            value={filters.countryId === null ? "" : String(filters.countryId)}
            onChange={(v) =>
              setFilters((p) => ({ ...p, countryId: v ? parseInt(v, 10) : null }))
            }
            options={[
              { value: "", label: "All countries" },
              ...availableCountries.map((c) => ({ value: String(c.id), label: c.name })),
            ]}
          />
          <FilterDropdown
            label="Fee min"
            value={filters.feeMin === null ? "" : String(filters.feeMin)}
            onChange={(v) =>
              setFilters((p) => {
                const next = v ? parseInt(v, 10) : null;
                // If user just raised Min above existing Max, clear Max (per spec).
                if (next !== null && p.feeMax !== null && next > p.feeMax) {
                  return { ...p, feeMin: next, feeMax: null };
                }
                return { ...p, feeMin: next };
              })
            }
            options={FEE_OPTIONS_FOR_MIN}
          />
          <FilterDropdown
            label="Fee max"
            value={filters.feeMax === null ? "" : String(filters.feeMax)}
            onChange={(v) =>
              setFilters((p) => {
                const next = v ? parseInt(v, 10) : null;
                // If user just lowered Max below existing Min, clear Min (per spec).
                if (next !== null && p.feeMin !== null && next < p.feeMin) {
                  return { ...p, feeMin: null, feeMax: next };
                }
                return { ...p, feeMax: next };
              })
            }
            options={FEE_OPTIONS_FOR_MAX}
          />
          <FilterDropdown
            label="From"
            value={filters.windowStart ?? ""}
            onChange={(v) => {
              hasInitializedWindow.current = true;
              setFilters((p) => ({ ...p, windowStart: v || null }));
            }}
            options={[
              { value: "", label: "Earliest" },
              ...availableWindows.map((w) => ({ value: w.value, label: w.label })),
            ]}
          />
          <FilterDropdown
            label="To"
            value={filters.windowEnd ?? ""}
            onChange={(v) => setFilters((p) => ({ ...p, windowEnd: v || null }))}
            options={[
              { value: "", label: "Latest" },
              ...availableWindows.map((w) => ({ value: w.value, label: w.label })),
            ]}
          />
          <label className="flex items-center gap-2 text-[12px] text-[#c5dace] cursor-pointer ml-auto">
            <input
              type="checkbox"
              checked={filters.completedOnly}
              onChange={(e) => setFilters((p) => ({ ...p, completedOnly: e.target.checked }))}
              className="accent-[#4ade80]"
            />
            Completed only
          </label>
        </div>

        {/* Rankings */}
        {best.length === 0 && worst.length === 0 && !rankingsLoading ? (
          <div className="py-10">
            <EmptyState
              message="No graded transfers match these filters yet. Try widening the time range."
              icon={ClipboardList}
            />
          </div>
        ) : (
          <GradeRankings best={best} worst={worst} loading={rankingsLoading} />
        )}

        {/* Club report cards */}
        <ClubReportCards
          selectedClubs={selectedClubs}
          reportCards={reportCards}
          loading={comparisonLoading}
          onAdd={handleAddClub}
          onRemove={handleRemoveClub}
        />
      </div>
    </div>
  );
}


function FilterDropdown({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="flex items-center gap-1.5 text-[11px] text-[#6b8a78]">
      <span className="uppercase tracking-[0.1em] font-medium">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg bg-white/[0.04] border border-white/[0.06] px-2 py-1 text-[12px] text-[#e8f0ec] focus:outline-none focus:border-[#4ade80]/30"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value} className="bg-[#0e1f16]">
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
