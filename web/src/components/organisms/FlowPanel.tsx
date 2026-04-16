import { useCallback, useEffect, useState } from "react";
import { useFilters } from "@/hooks/useFilters";
import { useCountryDetail } from "@/hooks/useCountryDetail";
import { EmptyState } from "@/components/molecules/EmptyState";
import { StatCard } from "@/components/molecules/StatCard";
import { PanelShell } from "./PanelShell";
import { TransferTable } from "./TransferTable";
import type { SortField } from "./TransferTable";
import { formatFee, formatCount } from "@/lib/format";
import { getFlag } from "@/lib/flags";
import type { TransferRow } from "@/types/transfer";

interface FlowPanelProps {
  /** Primary country (the spender side of the arc). */
  countryId: number;
  countryName: string;
  /** Counterpart country. */
  counterpartCountryId: number;
  counterpartCountryName: string;
  onClose: () => void;
}

type DirectionFilter = "both" | "to" | "from";

/** Detail panel for a country-to-country flow — summary cards, direction toggle, transfers. */
export function FlowPanel({
  countryId,
  countryName,
  counterpartCountryId,
  counterpartCountryName,
  onClose,
}: FlowPanelProps) {
  const { filters } = useFilters();
  const [sortBy, setSortBy] = useState<SortField>("fee");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [direction] = useState<DirectionFilter>("both");

  useEffect(() => { setPage(1); }, [countryId, counterpartCountryId, filters]);

  const { data, isLoading, error, retry } = useCountryDetail({
    countryId,
    counterpartCountryId,
    filters,
    sortBy,
    sortOrder,
    page,
  });

  const handleSort = useCallback((field: SortField) => {
    if (sortBy === field) {
      setSortOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setPage(1);
  }, [sortBy]);

  // Client-side direction filtering on the already-fetched transfers
  const filteredItems: TransferRow[] = data
    ? data.transfers.items.filter(() => {
        if (direction === "both") return true;
        return true;
      })
    : [];

  // Compute summary stats from the top clubs data
  const totalSpentByPrimary = data?.top_buying_clubs.reduce((sum, c) => sum + c.total_spent_eur, 0) ?? 0;
  const totalReceivedByPrimary = data?.top_selling_clubs.reduce((sum, c) => sum + c.total_received_eur, 0) ?? 0;

  return (
    <PanelShell
      isOpen={true}
      onClose={onClose}
      isLoading={isLoading && !data}
      error={error}
      onRetry={retry}
    >
      {data ? (
        <>
          {/* Header */}
          <div className="px-6 pt-5 pb-4 bg-gradient-to-b from-white/[0.03] to-transparent border-b border-white/[0.04]">
            <div className="flex items-center gap-2 pr-8">
              <span className="text-2xl">{getFlag(data.country.iso_code)}</span>
              <h2 className="text-lg font-semibold text-[#e8f0ec] tracking-tight">
                {countryName}
                <span className="text-[#4ade80] mx-2">↔</span>
                {counterpartCountryName}
              </h2>
            </div>
          </div>

          <div className="px-6 pt-5">
            {/* Summary cards */}
            <div className="grid grid-cols-2 gap-3 mb-5">
              <StatCard
                label={`${countryName} → ${counterpartCountryName}`}
                value={formatFee(totalSpentByPrimary)}
                badge={{
                  text: `${formatCount(data.top_buying_clubs.reduce((s, c) => s + c.transfer_count, 0))} transfers`,
                  variant: "danger",
                }}
              />
              <StatCard
                label={`${counterpartCountryName} → ${countryName}`}
                value={formatFee(totalReceivedByPrimary)}
                badge={{
                  text: `${formatCount(data.top_selling_clubs.reduce((s, c) => s + c.transfer_count, 0))} transfers`,
                  variant: "success",
                }}
              />
            </div>

            {/* Net flow */}
            <div className="mb-5 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-[11px] text-[#6b8a78]">Net flow: </span>
              <span className={`font-data text-[13px] tabular-nums ${totalSpentByPrimary > totalReceivedByPrimary ? "text-red-400" : "text-emerald-400"}`}>
                {formatFee(Math.abs(totalSpentByPrimary - totalReceivedByPrimary))}
              </span>
              <span className="text-[11px] text-[#6b8a78]">
                {" "}→ {totalSpentByPrimary > totalReceivedByPrimary ? counterpartCountryName : countryName}
              </span>
            </div>

            {/* Transfers */}
            <div>
              <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-2.5">
                Transfers <span className="font-data text-[#4a6555]">({formatCount(data.transfers.total)})</span>
              </h3>
              <TransferTable
                items={filteredItems}
                total={data.transfers.total}
                page={page}
                pageSize={data.transfers.page_size}
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={handleSort}
                onPageChange={setPage}
              />
            </div>
          </div>
        </>
      ) : (
        <div className="p-6"><EmptyState message="No transfer data found for this flow" /></div>
      )}
    </PanelShell>
  );
}
