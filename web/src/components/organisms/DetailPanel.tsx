import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowRight, ChevronLeft, ChevronRight, ExternalLink, X } from "lucide-react";
import { useFilters } from "@/hooks/useFilters";
import { useCountryDetail } from "@/hooks/useCountryDetail";
import { Badge } from "@/components/atoms/Badge";
import { Spinner } from "@/components/atoms/Spinner";
import { EmptyState } from "@/components/molecules/EmptyState";
import { ErrorState } from "@/components/molecules/ErrorState";
import { formatFee, formatCount, formatDate } from "@/lib/format";
import { getFlag } from "@/lib/flags";
import type { TopClub } from "@/types/club";

interface DetailPanelProps {
  countryId: number | null;
  counterpartCountryId?: number | null;
  counterpartCountryName?: string | null;
  onClose: () => void;
}

type SortField = "fee" | "date" | "player_name";

const POS_STYLE: Record<string, string> = {
  GK: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  DEF: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  MID: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  FWD: "bg-red-500/15 text-red-400 border-red-500/20",
};

/** Sliding country detail panel with refined glass treatment. */
export function DetailPanel({ countryId, counterpartCountryId, counterpartCountryName, onClose }: DetailPanelProps) {
  const navigate = useNavigate();
  const { filters } = useFilters();
  const [sortBy, setSortBy] = useState<SortField>("fee");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);

  useEffect(() => { setPage(1); }, [countryId, filters]);

  const { data, isLoading, error, retry } = useCountryDetail({ countryId, counterpartCountryId, filters, sortBy, sortOrder, page });

  const handleSort = useCallback((field: SortField) => {
    if (sortBy === field) {
      setSortOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setPage(1);
  }, [sortBy]);

  const isOpen = countryId !== null;
  const totalPages = data ? Math.ceil(data.transfers.total / data.transfers.page_size) : 0;

  function SortIcon({ field }: { field: SortField }) {
    if (sortBy !== field) return <span className="inline-block w-3" />;
    return sortOrder === "desc"
      ? <ArrowDown className="inline h-3 w-3 ml-0.5 text-[#4ade80]" />
      : <ArrowUp className="inline h-3 w-3 ml-0.5 text-[#4ade80]" />;
  }

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
    <div
      className={`shrink-0 border-l border-white/[0.06] bg-[#0c1a12] overflow-y-auto transition-all duration-300 ease-out z-40 ${
        isOpen ? "w-[35vw] min-w-[400px] max-w-[600px]" : "w-0 min-w-0 max-w-0"
      }`}
    >
      {isOpen && (
        <div className="relative">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1.5 rounded-lg text-[#6b8a78] hover:text-[#e8f0ec] hover:bg-white/[0.05] transition-all z-10"
          >
            <X className="h-4 w-4" />
          </button>

          {isLoading && !data ? (
            <div className="flex justify-center py-20"><Spinner size="lg" /></div>
          ) : error ? (
            <div className="p-6"><ErrorState message={error} onRetry={retry} /></div>
          ) : !data ? (
            <div className="p-6"><EmptyState message="Country not found" /></div>
          ) : (
            <>
              {/* Gradient header */}
              <div className="px-6 pt-5 pb-4 bg-gradient-to-b from-white/[0.03] to-transparent border-b border-white/[0.04]">
                <div className="flex items-center gap-3 mb-2 pr-8">
                  <span className="text-3xl">{getFlag(data.country.iso_code)}</span>
                  <div>
                    <h2 className="text-lg font-semibold text-[#e8f0ec] tracking-tight">
                      {data.country.name}
                      {counterpartCountryName && (
                        <span className="text-[#6b8a78]"> ↔ {counterpartCountryName}</span>
                      )}
                    </h2>
                    <Badge variant={data.country.net_spend_eur > 0 ? "danger" : "success"}>
                      {data.country.net_spend_eur > 0
                        ? `Net Spend: ${formatFee(data.country.net_spend_eur)}`
                        : `Net Revenue: ${formatFee(Math.abs(data.country.net_spend_eur))}`}
                    </Badge>
                  </div>
                </div>
              </div>

              <div className="px-6 pt-5">
                {/* Top Clubs */}
                <ClubList clubs={data.top_buying_clubs} label="Top Buying Clubs" valueKey="total_spent_eur" />
                <ClubList clubs={data.top_selling_clubs} label="Top Selling Clubs" valueKey="total_received_eur" />

                {/* Transfers Table */}
                <div>
                  <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-2.5">
                    Transfers <span className="font-data text-[#4a6555]">({formatCount(data.transfers.total)})</span>
                  </h3>

                  {data.transfers.total === 0 ? (
                    <EmptyState message="No transfers match your current filters" />
                  ) : (
                    <>
                      <div className="overflow-x-auto rounded-lg border border-white/[0.04]">
                        <table className="w-full text-[12px]">
                          <thead>
                            <tr className="bg-white/[0.02] text-[#6b8a78]">
                              <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em] cursor-pointer hover:text-[#c5dace] transition-colors" onClick={() => handleSort("player_name")}>
                                Player<SortIcon field="player_name" />
                              </th>
                              <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">From</th>
                              <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">To</th>
                              <th className="text-right px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em] cursor-pointer hover:text-[#c5dace] transition-colors" onClick={() => handleSort("fee")}>
                                Fee<SortIcon field="fee" />
                              </th>
                              <th className="text-center px-2 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">Pos</th>
                              <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em] cursor-pointer hover:text-[#c5dace] transition-colors" onClick={() => handleSort("date")}>
                                Date<SortIcon field="date" />
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            {data.transfers.items.map((t) => (
                              <tr key={t.transfer_id} className="border-t border-white/[0.03] hover:bg-white/[0.03] transition-colors">
                                <td className="px-3 py-2">
                                  {t.player_transfermarkt_url ? (
                                    <a href={t.player_transfermarkt_url} target="_blank" rel="noopener noreferrer" className="text-[#4ade80]/80 hover:text-[#4ade80] inline-flex items-center gap-1 transition-colors">
                                      {t.player_name}
                                      <ExternalLink className="h-2.5 w-2.5 opacity-40" />
                                    </a>
                                  ) : (
                                    <span className="text-[#c5dace]">{t.player_name}</span>
                                  )}
                                </td>
                                <td className="px-3 py-2 text-[#8fa898] truncate max-w-[120px]">{t.from_club_name}</td>
                                <td className="px-3 py-2 text-[#8fa898] truncate max-w-[120px]">{t.to_club_name}</td>
                                <td className="px-3 py-2 text-right font-data text-[#e8f0ec] tabular-nums">
                                  {formatFee(t.fee_eur)}
                                  {t.fee_is_loan && <span className="text-[#4a6555] text-[10px] ml-1">(loan)</span>}
                                </td>
                                <td className="px-2 py-2 text-center">
                                  {t.position_group && (
                                    <span className={`inline-flex items-center justify-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold border ${POS_STYLE[t.position_group] ?? ""}`}>
                                      {t.position_group}
                                    </span>
                                  )}
                                </td>
                                <td className="px-3 py-2 font-data text-[#6b8a78] text-[11px] whitespace-nowrap tabular-nums">
                                  {t.transfer_date ? formatDate(t.transfer_date) : t.transfer_window}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* Pagination */}
                      <div className="flex items-center justify-between mt-3 mb-6 text-[12px] text-[#6b8a78]">
                        <span className="font-data tabular-nums">
                          {(page - 1) * 20 + 1}–{Math.min(page * 20, data.transfers.total)} of {formatCount(data.transfers.total)}
                        </span>
                        <div className="flex items-center gap-0.5">
                          <button
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            disabled={page <= 1}
                            className="p-1.5 rounded-lg hover:bg-white/[0.05] disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                          >
                            <ChevronLeft className="h-3.5 w-3.5" />
                          </button>
                          <span className="px-2 font-data tabular-nums text-[#8fa898]">{page}/{totalPages}</span>
                          <button
                            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="p-1.5 rounded-lg hover:bg-white/[0.05] disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                          >
                            <ChevronRight className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
