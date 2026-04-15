import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, ExternalLink, X } from "lucide-react";
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
  onClose: () => void;
}

type SortField = "fee" | "date" | "player_name";

/** Sliding country detail panel. */
export function DetailPanel({ countryId, onClose }: DetailPanelProps) {
  const navigate = useNavigate();
  const { filters } = useFilters();
  const [sortBy, setSortBy] = useState<SortField>("fee");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);

  // Reset pagination when country or filters change
  useEffect(() => { setPage(1); }, [countryId, filters]);

  const { data, isLoading, error, retry } = useCountryDetail({ countryId, filters, sortBy, sortOrder, page });

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
    if (sortBy !== field) return null;
    return sortOrder === "desc"
      ? <ArrowDown className="inline h-3 w-3 ml-0.5" />
      : <ArrowUp className="inline h-3 w-3 ml-0.5" />;
  }

  function ClubList({ clubs, label, valueKey }: { clubs: TopClub[]; label: string; valueKey: "total_spent_eur" | "total_received_eur" }) {
    return (
      <div className="mb-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-[#8fa898] mb-2">{label}</h3>
        {clubs.length === 0 ? (
          <p className="text-sm text-[#8fa898]">No data</p>
        ) : (
          <div className="space-y-1.5">
            {clubs.map((c) => (
              <div key={c.club_id} className="flex items-center justify-between text-sm">
                <button
                  onClick={() => navigate(`/network/${c.club_id}`)}
                  className="text-[#4ade80] hover:underline text-left truncate mr-3"
                >
                  {c.club_name}
                </button>
                <span className="text-[#e8f0ec] tabular-nums whitespace-nowrap">
                  {formatFee(c[valueKey])}
                  <span className="text-[#8fa898] text-xs ml-1.5">({c.transfer_count})</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={`shrink-0 border-l border-[#2d4a38] bg-[#1e3a2a] overflow-y-auto transition-all duration-300 ease-out ${
        isOpen ? "w-[35vw] min-w-[400px] max-w-[600px]" : "w-0 min-w-0 max-w-0"
      }`}
    >
      {isOpen && (
        <div className="p-5 relative">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-3 right-3 p-1 text-[#8fa898] hover:text-[#e8f0ec] transition-colors z-10"
          >
            <X className="h-5 w-5" />
          </button>

          {isLoading && !data ? (
            <div className="flex justify-center py-16"><Spinner size="lg" /></div>
          ) : error ? (
            <ErrorState message={error} onRetry={retry} />
          ) : !data ? (
            <EmptyState message="Country not found" />
          ) : (
            <>
              {/* Header */}
              <div className="mb-5 pr-6">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-2xl">{getFlag(data.country.iso_code)}</span>
                  <h2 className="text-xl font-bold text-[#e8f0ec]">{data.country.name}</h2>
                </div>
                <Badge variant={data.country.net_spend_eur > 0 ? "danger" : "success"}>
                  {data.country.net_spend_eur > 0
                    ? `Net Spend: ${formatFee(data.country.net_spend_eur)}`
                    : `Net Revenue: ${formatFee(Math.abs(data.country.net_spend_eur))}`}
                </Badge>
              </div>

              {/* Top Clubs */}
              <ClubList clubs={data.top_buying_clubs} label="Top Buying Clubs" valueKey="total_spent_eur" />
              <ClubList clubs={data.top_selling_clubs} label="Top Selling Clubs" valueKey="total_received_eur" />

              {/* Transfers Table */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-[#8fa898] mb-2">
                  Transfers ({formatCount(data.transfers.total)})
                </h3>

                {data.transfers.total === 0 ? (
                  <EmptyState message="No transfers match your current filters" />
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-[#1a2e22] sticky top-0">
                          <tr className="text-[#8fa898] text-xs uppercase tracking-wider">
                            <th className="text-left px-3 py-2 cursor-pointer hover:text-[#e8f0ec]" onClick={() => handleSort("player_name")}>
                              Player<SortIcon field="player_name" />
                            </th>
                            <th className="text-left px-3 py-2">From</th>
                            <th className="text-left px-3 py-2">To</th>
                            <th className="text-right px-3 py-2 cursor-pointer hover:text-[#e8f0ec]" onClick={() => handleSort("fee")}>
                              Fee<SortIcon field="fee" />
                            </th>
                            <th className="text-left px-3 py-2">Pos</th>
                            <th className="text-left px-3 py-2 cursor-pointer hover:text-[#e8f0ec]" onClick={() => handleSort("date")}>
                              Date<SortIcon field="date" />
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.transfers.items.map((t, i) => (
                            <tr key={t.transfer_id} className={`border-b border-[#2d4a38] hover:bg-[#243d2e] transition-colors ${i % 2 === 1 ? "bg-[#223a2d]" : ""}`}>
                              <td className="px-3 py-2">
                                {t.player_transfermarkt_url ? (
                                  <a href={t.player_transfermarkt_url} target="_blank" rel="noopener noreferrer" className="text-[#4ade80] hover:underline inline-flex items-center gap-1">
                                    {t.player_name}
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                ) : (
                                  <span className="text-[#e8f0ec]">{t.player_name}</span>
                                )}
                              </td>
                              <td className="px-3 py-2 text-[#e8f0ec]">{t.from_club_name}</td>
                              <td className="px-3 py-2 text-[#e8f0ec]">{t.to_club_name}</td>
                              <td className="px-3 py-2 text-right text-[#e8f0ec] tabular-nums">
                                {formatFee(t.fee_eur)}
                                {t.fee_is_loan && <span className="text-[#8fa898] text-xs ml-1">(loan)</span>}
                              </td>
                              <td className="px-3 py-2">
                                {t.position_group && (
                                  <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                                    { GK: "bg-amber-900/40 text-amber-400", DEF: "bg-blue-900/40 text-blue-400", MID: "bg-green-900/40 text-green-400", FWD: "bg-red-900/40 text-red-400" }[t.position_group] ?? ""
                                  }`}>
                                    {t.position_group}
                                  </span>
                                )}
                              </td>
                              <td className="px-3 py-2 text-[#8fa898] whitespace-nowrap">
                                {t.transfer_date ? formatDate(t.transfer_date) : t.transfer_window}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination */}
                    <div className="flex items-center justify-between mt-3 text-sm text-[#8fa898]">
                      <span>
                        Showing {(page - 1) * 20 + 1}-{Math.min(page * 20, data.transfers.total)} of {formatCount(data.transfers.total)}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                          disabled={page <= 1}
                          className="p-1 rounded hover:bg-[#243d2e] disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </button>
                        <span className="px-2 tabular-nums">{page} / {totalPages}</span>
                        <button
                          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                          disabled={page >= totalPages}
                          className="p-1 rounded hover:bg-[#243d2e] disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
