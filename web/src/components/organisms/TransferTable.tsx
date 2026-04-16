import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { EmptyState } from "@/components/molecules/EmptyState";
import { formatFee, formatCount, formatDate } from "@/lib/format";
import type { TransferRow } from "@/types/transfer";

type SortField = "fee" | "date" | "player_name";

const POS_STYLE: Record<string, string> = {
  GK: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  DEF: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  MID: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  FWD: "bg-red-500/15 text-red-400 border-red-500/20",
};

interface TransferTableProps {
  items: TransferRow[];
  total: number;
  page: number;
  pageSize: number;
  sortBy: SortField;
  sortOrder: "asc" | "desc";
  onSort: (field: SortField) => void;
  onPageChange: (page: number) => void;
}

/** Sortable, paginated transfer table. */
export function TransferTable({
  items,
  total,
  page,
  pageSize,
  sortBy,
  sortOrder,
  onSort,
  onPageChange,
}: TransferTableProps) {
  const totalPages = Math.ceil(total / pageSize);

  function SortIcon({ field }: { field: SortField }) {
    if (sortBy !== field) return <span className="inline-block w-3" />;
    return sortOrder === "desc"
      ? <ArrowDown className="inline h-3 w-3 ml-0.5 text-[#4ade80]" />
      : <ArrowUp className="inline h-3 w-3 ml-0.5 text-[#4ade80]" />;
  }

  if (total === 0) {
    return <EmptyState message="No transfers match your current filters" />;
  }

  return (
    <>
      <div className="overflow-x-auto rounded-lg border border-white/[0.04]">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="bg-white/[0.02] text-[#6b8a78]">
              <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em] cursor-pointer hover:text-[#c5dace] transition-colors" onClick={() => onSort("player_name")}>
                Player<SortIcon field="player_name" />
              </th>
              <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">From</th>
              <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">To</th>
              <th className="text-right px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em] cursor-pointer hover:text-[#c5dace] transition-colors" onClick={() => onSort("fee")}>
                Fee<SortIcon field="fee" />
              </th>
              <th className="text-center px-2 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">Pos</th>
              <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em] cursor-pointer hover:text-[#c5dace] transition-colors" onClick={() => onSort("date")}>
                Date<SortIcon field="date" />
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.transfer_id} className="border-t border-white/[0.03] hover:bg-white/[0.03] transition-colors">
                <td className="px-3 py-2">
                  <span className="inline-flex items-center gap-1">
                    {t.player_id ? (
                      <Link to={`/players/${t.player_id}`} className="text-[#4ade80]/80 hover:text-[#4ade80] transition-colors">
                        {t.player_name}
                      </Link>
                    ) : (
                      <span className="text-[#c5dace]">{t.player_name}</span>
                    )}
                    {t.player_transfermarkt_url && (
                      <a href={t.player_transfermarkt_url} target="_blank" rel="noopener noreferrer" className="text-[#6b8a78] hover:text-[#4ade80] transition-colors" title="View on Transfermarkt">
                        <ExternalLink className="h-2.5 w-2.5" />
                      </a>
                    )}
                  </span>
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

      <div className="flex items-center justify-between mt-3 mb-6 text-[12px] text-[#6b8a78]">
        <span className="font-data tabular-nums">
          {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {formatCount(total)}
        </span>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => onPageChange(Math.max(1, page - 1))}
            disabled={page <= 1}
            className="p-1.5 rounded-lg hover:bg-white/[0.05] disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className="px-2 font-data tabular-nums text-[#8fa898]">{page}/{totalPages}</span>
          <button
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="p-1.5 rounded-lg hover:bg-white/[0.05] disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </>
  );
}

export type { SortField };
