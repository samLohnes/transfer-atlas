import { formatFee, formatDate } from "@/lib/format";
import type { TransferRow as TransferRowType } from "@/types/transfer";

interface TransferRowProps {
  transfer: TransferRowType;
}

const positionColors: Record<string, string> = {
  GK: "bg-amber-900/40 text-amber-400",
  DEF: "bg-blue-900/40 text-blue-400",
  MID: "bg-green-900/40 text-green-400",
  FWD: "bg-red-900/40 text-red-400",
};

/** A single row in the transfer table. */
export function TransferRow({ transfer }: TransferRowProps) {
  return (
    <tr className="border-b border-[#2d4a38] hover:bg-[#243d2e] transition-colors">
      <td className="px-3 py-2 text-sm">
        {transfer.player_transfermarkt_url ? (
          <a
            href={transfer.player_transfermarkt_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#4ade80] hover:underline"
          >
            {transfer.player_name}
          </a>
        ) : (
          <span className="text-[#e8f0ec]">{transfer.player_name}</span>
        )}
      </td>
      <td className="px-3 py-2 text-sm text-[#e8f0ec]">{transfer.from_club_name}</td>
      <td className="px-3 py-2 text-sm text-[#e8f0ec]">{transfer.to_club_name}</td>
      <td className="px-3 py-2 text-sm text-[#e8f0ec] tabular-nums text-right">
        {formatFee(transfer.fee_eur)}
        {transfer.fee_is_loan && <span className="ml-1 text-[#8fa898] text-xs">(loan)</span>}
      </td>
      <td className="px-3 py-2 text-sm">
        {transfer.position_group && (
          <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${positionColors[transfer.position_group] ?? ""}`}>
            {transfer.position_group}
          </span>
        )}
      </td>
      <td className="px-3 py-2 text-sm text-[#8fa898]">
        {transfer.transfer_date ? formatDate(transfer.transfer_date) : transfer.transfer_window}
      </td>
    </tr>
  );
}
