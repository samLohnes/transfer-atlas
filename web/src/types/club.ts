/** A club search result. */
export interface ClubSearchResult {
  club_id: number;
  club_name: string;
  country_name: string;
  league_name: string | null;
}

/** A top club summary in the country detail panel. */
export interface TopClub {
  club_id: number;
  club_name: string;
  total_spent_eur: number;
  total_received_eur: number;
  transfer_count: number;
}

/** Center club in a network graph. */
export interface CenterClub {
  club_id: number;
  club_name: string;
  country_id?: number;
  country_name?: string;
}

/** A country-level edge in the network graph. */
export interface CountryEdge {
  country_id: number;
  country_name: string;
  total_spent_eur: number;
  total_received_eur: number;
  transfer_count: number;
}

/** An individual transfer within a network edge. */
export interface NetworkTransfer {
  transfer_id: number;
  player_name: string;
  player_transfermarkt_url: string | null;
  fee_eur: number | null;
  fee_is_loan: boolean;
  direction: "bought" | "sold";
  position_group: string | null;
  transfer_window: string;
}

/** A club-level edge in the expanded network graph. */
export interface ClubEdge {
  club_id: number;
  club_name: string;
  total_spent_eur: number;
  total_received_eur: number;
  transfer_count: number;
  transfers: NetworkTransfer[];
}
