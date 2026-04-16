import { useCallback, useEffect, useState } from "react";
import { ArrowLeftRight, ArrowRight } from "lucide-react";
import { useFilters } from "@/hooks/useFilters";
import { useCountryDetail } from "@/hooks/useCountryDetail";
import { EmptyState } from "@/components/molecules/EmptyState";
import { StatCard } from "@/components/molecules/StatCard";
import { PanelShell } from "./PanelShell";
import { TransferTable } from "./TransferTable";
import type { SortField } from "./TransferTable";
import { formatFee, formatCount } from "@/lib/format";
import { getFlag } from "@/lib/flags";

interface FlowPanelProps {
  countryId: number;
  countryName: string;
  counterpartCountryId: number;
  counterpartCountryName: string;
  onClose: () => void;
}

type DirectionFilter = "both" | "buying" | "selling";

/** Detail panel for a country-to-country flow. */
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
  const [direction, setDirection] = useState<DirectionFilter>("both");

  useEffect(() => { setPage(1); }, [countryId, counterpartCountryId, filters, direction]);

  const { data, isLoading, error, retry } = useCountryDetail({
    countryId,
    counterpartCountryId,
    direction: direction === "both" ? null : direction,
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
                label={`${countryName} buys from ${counterpartCountryName}`}
                value={formatFee(totalSpentByPrimary)}
                badge={{
                  text: `${formatCount(data.top_buying_clubs.reduce((s, c) => s + c.transfer_count, 0))} transfers`,
                  variant: "danger",
                }}
              />
              <StatCard
                label={`${countryName} sells to ${counterpartCountryName}`}
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

            {/* Direction toggle + Transfers */}
            <div>
              <div className="flex items-center justify-between mb-2.5">
                <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78]">
                  Transfers <span className="font-data text-[#4a6555]">({formatCount(data.transfers.total)})</span>
                </h3>

                {/* Direction toggle */}
                <div className="flex rounded-lg overflow-hidden border border-white/[0.06] bg-white/[0.02]">
                  <button
                    onClick={() => setDirection("both")}
                    className={`px-2 py-1 text-[10px] font-medium flex items-center gap-1 transition-all duration-200 ${
                      direction === "both"
                        ? "bg-[#4ade80]/15 text-[#4ade80]"
                        : "text-[#6b8a78] hover:text-[#c5dace]"
                    }`}
                    title="Show all transfers"
                  >
                    <ArrowLeftRight className="h-3 w-3" />
                    Both
                  </button>
                  <button
                    onClick={() => setDirection("buying")}
                    className={`px-2 py-1 text-[10px] font-medium flex items-center gap-1 transition-all duration-200 ${
                      direction === "buying"
                        ? "bg-red-500/15 text-red-400"
                        : "text-[#6b8a78] hover:text-[#c5dace]"
                    }`}
                    title={`${countryName} buying`}
                  >
                    <ArrowRight className="h-3 w-3" />
                    {countryName} buys
                  </button>
                  <button
                    onClick={() => setDirection("selling")}
                    className={`px-2 py-1 text-[10px] font-medium flex items-center gap-1 transition-all duration-200 ${
                      direction === "selling"
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "text-[#6b8a78] hover:text-[#c5dace]"
                    }`}
                    title={`${countryName} selling`}
                  >
                    <ArrowRight className="h-3 w-3 rotate-180" />
                    {countryName} sells
                  </button>
                </div>
              </div>

              <TransferTable
                items={data.transfers.items}
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
