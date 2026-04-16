import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeftRight, ArrowRight, ArrowDownToLine, ArrowUpFromLine } from "lucide-react";
import { useFilters } from "@/hooks/useFilters";
import { useCountryDetail } from "@/hooks/useCountryDetail";
import { Badge } from "@/components/atoms/Badge";
import { EmptyState } from "@/components/molecules/EmptyState";
import { PanelShell } from "./PanelShell";
import { TransferTable } from "./TransferTable";
import type { SortField } from "./TransferTable";
import { formatFee, formatCount } from "@/lib/format";
import { getFlag } from "@/lib/flags";
import type { TopClub } from "@/types/club";

interface CountryPanelProps {
  countryId: number | null;
  onClose: () => void;
}

/** Detail panel for a single country — top clubs and transfers. */
export function CountryPanel({ countryId, onClose }: CountryPanelProps) {
  const navigate = useNavigate();
  const { filters } = useFilters();
  const [sortBy, setSortBy] = useState<SortField>("fee");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [direction, setDirection] = useState<"both" | "buying" | "selling">("both");

  useEffect(() => { setPage(1); }, [countryId, filters, direction]);

  const { data, isLoading, error, retry } = useCountryDetail({
    countryId,
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

  function ClubList({ clubs, label, valueKey }: { clubs: TopClub[]; label: string; valueKey: "total_spent_eur" | "total_received_eur" }) {
    return (
      <div className="mb-5">
        <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-2.5">{label}</h3>
        {clubs.length === 0 ? (
          <p className="text-[13px] text-[#4a6555]">No data</p>
        ) : (
          <div className="space-y-1">
            {clubs.map((c) => (
              <button
                key={c.club_id}
                onClick={() => navigate(`/network/${c.club_id}`)}
                className="w-full flex items-center justify-between text-[13px] px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-[#4ade80]/20 transition-all duration-200 group"
              >
                <span className="text-[#c5dace] group-hover:text-[#4ade80] truncate mr-3 flex items-center gap-1.5 transition-colors">
                  {c.club_name}
                  <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
                </span>
                <span className="font-data text-[#e8f0ec] tabular-nums whitespace-nowrap text-[12px]">
                  {formatFee(c[valueKey])}
                  <span className="text-[#4a6555] ml-1.5">({c.transfer_count})</span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <PanelShell
      isOpen={countryId !== null}
      onClose={onClose}
      isLoading={isLoading && !data}
      error={error}
      onRetry={retry}
    >
      {data ? (
        <>
          <div className="px-6 pt-5 pb-4 bg-gradient-to-b from-white/[0.03] to-transparent border-b border-white/[0.04]">
            <div className="flex items-center gap-3 mb-2 pr-8">
              <span className="text-3xl">{getFlag(data.country.iso_code)}</span>
              <div>
                <h2 className="text-lg font-semibold text-[#e8f0ec] tracking-tight">{data.country.name}</h2>
                <Badge variant={data.country.net_spend_eur > 0 ? "danger" : "success"}>
                  {data.country.net_spend_eur > 0
                    ? `Net Spend: ${formatFee(data.country.net_spend_eur)}`
                    : `Net Revenue: ${formatFee(Math.abs(data.country.net_spend_eur))}`}
                </Badge>
              </div>
            </div>
          </div>

          <div className="px-6 pt-5">
            <ClubList clubs={data.top_buying_clubs} label="Top Buying Clubs" valueKey="total_spent_eur" />
            <ClubList clubs={data.top_selling_clubs} label="Top Selling Clubs" valueKey="total_received_eur" />

            <div>
              <div className="flex items-center justify-between mb-2.5">
                <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78]">
                  Transfers <span className="font-data text-[#4a6555]">({formatCount(data.transfers.total)})</span>
                </h3>

                <div className="flex rounded-lg overflow-hidden border border-white/[0.06] bg-white/[0.02]">
                  <button
                    onClick={() => setDirection("both")}
                    className={`px-2 py-1 text-[10px] font-medium flex items-center gap-1 transition-all duration-200 ${
                      direction === "both"
                        ? "bg-[#4ade80]/15 text-[#4ade80]"
                        : "text-[#6b8a78] hover:text-[#c5dace]"
                    }`}
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
                  >
                    <ArrowDownToLine className="h-3 w-3" />
                    Buying
                  </button>
                  <button
                    onClick={() => setDirection("selling")}
                    className={`px-2 py-1 text-[10px] font-medium flex items-center gap-1 transition-all duration-200 ${
                      direction === "selling"
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "text-[#6b8a78] hover:text-[#c5dace]"
                    }`}
                  >
                    <ArrowUpFromLine className="h-3 w-3" />
                    Selling
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
        <div className="p-6"><EmptyState message="Country not found" /></div>
      )}
    </PanelShell>
  );
}
