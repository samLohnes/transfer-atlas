import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Network } from "lucide-react";
import { PanelShell } from "./PanelShell";
import { TransferTable } from "./TransferTable";
import type { SortField } from "./TransferTable";
import { StatCard } from "@/components/molecules/StatCard";
import { formatFee, formatCount } from "@/lib/format";
import type { ClubNetworkExpandResponse } from "@/types/api";
import type { CountryEdge, ClubEdge, NetworkTransfer } from "@/types/club";
import type { TransferRow } from "@/types/transfer";

interface NetworkDetailPanelProps {
  /** The center club's name. */
  centerClubName: string;
  /** What was clicked — country or club. */
  selection:
    | { type: "country"; countryId: number; countryName: string; edge: CountryEdge; expandedData?: ClubNetworkExpandResponse }
    | { type: "club"; clubId: number; clubName: string; clubEdge: ClubEdge };
  onClose: () => void;
}

/** Convert NetworkTransfer items to TransferRow format for the shared table. */
function toTransferRows(transfers: NetworkTransfer[], clubName: string, centerClubName: string): TransferRow[] {
  return transfers.map((t) => ({
    transfer_id: t.transfer_id,
    player_name: t.player_name,
    player_transfermarkt_url: t.player_transfermarkt_url,
    from_club_name: t.direction === "bought" ? clubName : centerClubName,
    from_club_id: 0,
    to_club_name: t.direction === "bought" ? centerClubName : clubName,
    to_club_id: 0,
    fee_eur: t.fee_eur,
    fee_is_loan: t.fee_is_loan,
    position_group: t.position_group,
    transfer_window: t.transfer_window,
    transfer_date: null,
  }));
}

export type { NetworkDetailPanelProps };

/** Detail sidebar for network graph — shows transfers for a clicked country or club. */
export function NetworkDetailPanel({ centerClubName, selection, onClose }: NetworkDetailPanelProps) {
  const navigate = useNavigate();
  const [sortBy, setSortBy] = useState<SortField>("fee");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const handleSort = useCallback((field: SortField) => {
    if (sortBy === field) {
      setSortOrder((o) => (o === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setPage(1);
  }, [sortBy]);

  // Build transfer rows and stats based on selection type
  let title: string;
  let totalSpent: number;
  let totalReceived: number;
  let transferCount: number;
  let allRows: TransferRow[];
  let showRecenterButton = false;
  let recenterId: number | undefined;

  if (selection.type === "club") {
    const { clubName, clubId, clubEdge } = selection;
    title = clubName;
    totalSpent = clubEdge.total_spent_eur;
    totalReceived = clubEdge.total_received_eur;
    transferCount = clubEdge.transfer_count;
    allRows = toTransferRows(clubEdge.transfers, clubName, centerClubName);
    showRecenterButton = true;
    recenterId = clubId;
  } else {
    const { countryName, edge, expandedData } = selection;
    title = countryName;
    totalSpent = edge.total_spent_eur;
    totalReceived = edge.total_received_eur;
    transferCount = edge.transfer_count;

    // If we have expanded data, show all transfers from all clubs in this country
    if (expandedData) {
      allRows = expandedData.club_edges.flatMap((ce) =>
        toTransferRows(ce.transfers, ce.club_name, centerClubName)
      );
    } else {
      allRows = [];
    }
  }

  // Client-side sort
  const sorted = [...allRows].sort((a, b) => {
    const dir = sortOrder === "desc" ? -1 : 1;
    if (sortBy === "fee") return dir * ((a.fee_eur ?? -1) - (b.fee_eur ?? -1));
    if (sortBy === "player_name") return dir * a.player_name.localeCompare(b.player_name);
    if (sortBy === "date") return dir * (a.transfer_window.localeCompare(b.transfer_window));
    return 0;
  });

  // Client-side pagination
  const totalRows = sorted.length;
  const paginated = sorted.slice((page - 1) * pageSize, page * pageSize);

  return (
    <PanelShell isOpen={true} onClose={onClose} isLoading={false} error={null} onRetry={() => {}}>
      {/* Header */}
      <div className="px-6 pt-5 pb-4 bg-gradient-to-b from-white/[0.03] to-transparent border-b border-white/[0.04]">
        <div className="pr-8">
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-[#6b8a78] mb-1">
            {centerClubName} ↔
          </p>
          <h2 className="text-lg font-semibold text-[#e8f0ec] tracking-tight">{title}</h2>
        </div>

        {showRecenterButton && recenterId && (
          <button
            onClick={() => navigate(`/network/${recenterId}`)}
            className="mt-3 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-white/[0.04] border border-white/[0.06] text-[#c5dace] hover:bg-white/[0.06] hover:border-[#4ade80]/20 hover:text-[#4ade80] transition-all duration-200"
          >
            <Network className="h-3 w-3" />
            View {title}'s network
          </button>
        )}
      </div>

      <div className="px-6 pt-5">
        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <StatCard
            label={`${centerClubName} spent`}
            value={formatFee(totalSpent)}
            badge={{ text: "buying", variant: "danger" }}
          />
          <StatCard
            label={`${centerClubName} received`}
            value={formatFee(totalReceived)}
            badge={{ text: "selling", variant: "success" }}
          />
        </div>

        {/* Net */}
        <div className="mb-5 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
          <span className="text-[11px] text-[#6b8a78]">Net: </span>
          <span className={`font-data text-[13px] tabular-nums ${totalSpent > totalReceived ? "text-red-400" : "text-emerald-400"}`}>
            {formatFee(Math.abs(totalSpent - totalReceived))}
          </span>
          <span className="text-[11px] text-[#6b8a78]">
            {totalSpent > totalReceived ? " spent" : " received"}
          </span>
          <span className="text-[11px] text-[#6b8a78] ml-2">
            ({formatCount(transferCount)} transfers)
          </span>
        </div>

        {/* Transfers */}
        <div>
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-2.5">
            Transfers <span className="font-data text-[#4a6555]">({formatCount(totalRows)})</span>
          </h3>
          <TransferTable
            items={paginated}
            total={totalRows}
            page={page}
            pageSize={pageSize}
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSort={handleSort}
            onPageChange={setPage}
          />
        </div>
      </div>
    </PanelShell>
  );
}
