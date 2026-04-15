/** An in-scope country with geographic coordinates. */
export interface Country {
  id: number;
  name: string;
  iso_code: string;
  latitude: number;
  longitude: number;
}

/** A directional flow between two countries. */
export interface CountryFlow {
  from_country_id: number;
  from_country_name: string;
  to_country_id: number;
  to_country_name: string;
  total_fee_eur: number;
  transfer_count: number;
  loan_count: number;
}

/** Per-country net spend summary. */
export interface CountrySummary {
  country_id: number;
  country_name: string;
  total_spent_eur: number;
  total_received_eur: number;
  net_spend_eur: number;
}

/** Country detail header. */
export interface CountryDetail {
  id: number;
  name: string;
  iso_code: string;
  net_spend_eur: number;
}
