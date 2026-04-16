/** A player search result. */
export interface PlayerSearchResult {
  player_id: number;
  player_name: string;
  position: string | null;
  position_group: string | null;
  nationality: string | null;
}

/** A transfer in the player's career. */
export interface PlayerTransfer {
  transfer_id: number;
  from_club_id: number;
  from_club_name: string;
  to_club_id: number;
  to_club_name: string;
  fee_eur: number | null;
  fee_is_loan: boolean;
  transfer_date: string | null;
  transfer_window: string;
  season: string;
}

/** A market valuation data point. */
export interface PlayerValuation {
  date: string;
  value_eur: number;
}

/** Full player profile. */
export interface PlayerDetail {
  player_id: number;
  name: string;
  date_of_birth: string | null;
  position: string | null;
  position_group: string | null;
  nationality: string | null;
  transfermarkt_url: string | null;
  transfers: PlayerTransfer[];
  valuations: PlayerValuation[];
}
