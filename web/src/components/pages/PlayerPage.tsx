import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ExternalLink, User } from "lucide-react";
import { fetchPlayerDetail } from "@/lib/api";
import { formatFee, formatDate } from "@/lib/format";
import { Spinner } from "@/components/atoms/Spinner";
import { EmptyState } from "@/components/molecules/EmptyState";
import { ErrorState } from "@/components/molecules/ErrorState";
import { PlayerSearchBar } from "@/components/molecules/PlayerSearchBar";
import { CareerTimeline } from "@/components/organisms/CareerTimeline";
import { ValueChart } from "@/components/organisms/ValueChart";
import type { PlayerDetail } from "@/types/player";

const POS_STYLE: Record<string, string> = {
  GK: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  DEF: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  MID: "bg-emerald-500/15 text-emerald-400 border-emerald-500/20",
  FWD: "bg-red-500/15 text-red-400 border-red-500/20",
};

/** Player profile page. */
export function PlayerPage() {
  const { playerId } = useParams<{ playerId: string }>();
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!playerId) { setPlayer(null); return; }
    setIsLoading(true);
    setError(null);
    fetchPlayerDetail(parseInt(playerId, 10))
      .then(setPlayer)
      .catch((err) => { console.error(err); setError("Failed to load player data."); setPlayer(null); })
      .finally(() => setIsLoading(false));
  }, [playerId]);

  // Compute age
  const age = player?.date_of_birth
    ? Math.floor((Date.now() - new Date(player.date_of_birth).getTime()) / (365.25 * 24 * 60 * 60 * 1000))
    : null;

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
      {/* Search bar */}
      <div className="flex justify-center py-3 px-4 shrink-0 bg-[#0e1f16]/60 backdrop-blur-lg border-b border-white/[0.04]">
        <PlayerSearchBar className="w-full max-w-[480px]" />
      </div>

      {!playerId ? (
        <div className="flex-1 flex items-center justify-center">
          <EmptyState message="Search for a player to view their career and market value" icon={User} />
        </div>
      ) : isLoading ? (
        <div className="flex-1 flex items-center justify-center"><Spinner size="lg" /></div>
      ) : error ? (
        <div className="flex-1 flex items-center justify-center"><ErrorState message={error} /></div>
      ) : player ? (
        <div className="max-w-[1000px] mx-auto w-full px-6 py-6 space-y-6">
          {/* Header */}
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center shrink-0">
              <span className="text-2xl font-bold text-[#4ade80]">
                {player.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}
              </span>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold text-[#e8f0ec] tracking-tight">{player.name}</h1>
                {player.transfermarkt_url && (
                  <a href={player.transfermarkt_url} target="_blank" rel="noopener noreferrer"
                    className="text-[#6b8a78] hover:text-[#4ade80] transition-colors" title="View on Transfermarkt">
                    <ExternalLink className="h-4 w-4" />
                  </a>
                )}
              </div>
              <div className="flex items-center gap-2 text-[13px] text-[#8fa898]">
                {player.position && (
                  <span className={`inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold border ${POS_STYLE[player.position_group ?? ""] ?? "bg-white/[0.04] text-[#8fa898] border-white/[0.06]"}`}>
                    {player.position}
                  </span>
                )}
                {player.nationality && <span>{player.nationality}</span>}
                {age !== null && <span className="text-white/10">·</span>}
                {age !== null && <span>Age {age}</span>}
                {player.date_of_birth && <span className="text-white/10">·</span>}
                {player.date_of_birth && <span>Born {formatDate(player.date_of_birth)}</span>}
              </div>
            </div>
          </div>

          {/* Career Timeline */}
          {player.transfers.length > 0 && (
            <div>
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-3">Career Path</h2>
              <CareerTimeline transfers={player.transfers} />
            </div>
          )}

          {/* Market Value Chart */}
          {player.valuations.length > 0 && (
            <div>
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-3">Market Value</h2>
              <ValueChart valuations={player.valuations} transfers={player.transfers} />
            </div>
          )}

          {/* Transfer History Table */}
          {player.transfers.length > 0 && (
            <div>
              <h2 className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#6b8a78] mb-3">
                Transfer History <span className="font-data text-[#4a6555]">({player.transfers.length})</span>
              </h2>
              <div className="overflow-x-auto rounded-lg border border-white/[0.04]">
                <table className="w-full text-[12px]">
                  <thead>
                    <tr className="bg-white/[0.02] text-[#6b8a78]">
                      <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">Date</th>
                      <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">From</th>
                      <th className="text-left px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">To</th>
                      <th className="text-right px-3 py-2.5 font-medium text-[10px] uppercase tracking-[0.1em]">Fee</th>
                    </tr>
                  </thead>
                  <tbody>
                    {player.transfers.map((t) => (
                      <tr key={t.transfer_id} className="border-t border-white/[0.03] hover:bg-white/[0.03] transition-colors">
                        <td className="px-3 py-2 font-data text-[#8fa898] tabular-nums whitespace-nowrap">
                          {t.transfer_date ? formatDate(t.transfer_date) : t.transfer_window}
                        </td>
                        <td className="px-3 py-2 text-[#c5dace]">{t.from_club_name}</td>
                        <td className="px-3 py-2 text-[#c5dace]">{t.to_club_name}</td>
                        <td className="px-3 py-2 text-right font-data text-[#e8f0ec] tabular-nums">
                          {formatFee(t.fee_eur)}
                          {t.fee_is_loan && <span className="text-[#4a6555] text-[10px] ml-1">(loan)</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
