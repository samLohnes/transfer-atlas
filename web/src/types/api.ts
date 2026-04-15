import type { Country, CountryDetail, CountryFlow, CountrySummary } from "./country";
import type { CenterClub, ClubEdge, ClubSearchResult, CountryEdge, TopClub } from "./club";
import type { PaginatedTransfers } from "./transfer";
import type { TransferWindow } from "./filter";

/** Pipeline metadata for the data freshness indicator. */
export interface PipelineMetadata {
  last_ingestion_at: string;
  records_processed: number;
  source_commit_hash: string | null;
}

/** GET /countries response. */
export interface CountriesResponse {
  countries: Country[];
}

/** GET /flows/countries response. */
export interface CountryFlowsResponse {
  flows: CountryFlow[];
  country_summaries: CountrySummary[];
}

/** GET /countries/{id}/detail response. */
export interface CountryDetailResponse {
  country: CountryDetail;
  top_buying_clubs: TopClub[];
  top_selling_clubs: TopClub[];
  transfers: PaginatedTransfers;
}

/** GET /clubs/search response. */
export interface ClubSearchResponse {
  clubs: ClubSearchResult[];
}

/** GET /clubs/{id}/network response. */
export interface ClubNetworkResponse {
  center_club: CenterClub;
  country_edges: CountryEdge[];
}

/** GET /clubs/{id}/network/{country_id} response. */
export interface ClubNetworkExpandResponse {
  center_club: CenterClub;
  country: { country_id: number; country_name: string };
  club_edges: ClubEdge[];
}

/** GET /filters/windows response. */
export interface WindowsResponse {
  windows: TransferWindow[];
}
