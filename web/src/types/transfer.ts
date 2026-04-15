/** An individual transfer record in the detail panel. */
export interface TransferRow {
  transfer_id: number;
  player_name: string;
  player_transfermarkt_url: string | null;
  from_club_name: string;
  from_club_id: number;
  to_club_name: string;
  to_club_id: number;
  fee_eur: number | null;
  fee_is_loan: boolean;
  position_group: string | null;
  transfer_window: string;
  transfer_date: string | null;
}

/** Paginated transfers response. */
export interface PaginatedTransfers {
  items: TransferRow[];
  total: number;
  page: number;
  page_size: number;
}
