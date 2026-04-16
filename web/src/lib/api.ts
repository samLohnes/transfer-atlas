import type { FilterState } from "@/types/filter";
import type { PlayerDetail, PlayerSearchResult } from "@/types/player";
import type {
  ClubNetworkExpandResponse,
  ClubNetworkResponse,
  ClubSearchResponse,
  CountriesResponse,
  CountryDetailResponse,
  CountryFlowsResponse,
  PipelineMetadata,
  WindowsResponse,
} from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

/** Build query string from filter state, omitting null/default values. */
function filterParams(filters: FilterState): URLSearchParams {
  const params = new URLSearchParams();

  if (filters.windowStart) params.set("window_start", filters.windowStart);
  if (filters.windowEnd) params.set("window_end", filters.windowEnd);
  if (filters.transferType !== "all") params.set("transfer_type", filters.transferType);
  if (filters.feeMin > 0) params.set("fee_min", String(filters.feeMin));
  if (filters.feeMax !== null) params.set("fee_max", String(filters.feeMax));
  if (filters.positionGroups.length > 0) params.set("position_group", filters.positionGroups.join(","));
  if (filters.ageMin !== null) params.set("age_min", String(filters.ageMin));
  if (filters.ageMax !== null) params.set("age_max", String(filters.ageMax));
  if (filters.countryIds.length > 0) params.set("country_ids", filters.countryIds.join(","));

  return params;
}

/** Generic fetch wrapper with error handling. */
async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

/** Build a URL with optional query params. */
function buildUrl(path: string, params?: URLSearchParams): string {
  const qs = params?.toString();
  return qs ? `${BASE_URL}${path}?${qs}` : `${BASE_URL}${path}`;
}

export async function fetchMetadata(): Promise<PipelineMetadata> {
  return fetchJson<PipelineMetadata>(buildUrl("/metadata"));
}

export async function fetchCountries(): Promise<CountriesResponse> {
  return fetchJson<CountriesResponse>(buildUrl("/countries"));
}

export async function fetchCountryFlows(filters: FilterState): Promise<CountryFlowsResponse> {
  return fetchJson<CountryFlowsResponse>(buildUrl("/flows/countries", filterParams(filters)));
}

export async function fetchCountryDetail(
  countryId: number,
  filters: FilterState,
  pagination: { sortBy?: string; sortOrder?: string; page?: number; pageSize?: number } = {},
  counterpartCountryId?: number | null,
  direction?: string | null,
): Promise<CountryDetailResponse> {
  const params = filterParams(filters);
  if (pagination.sortBy) params.set("sort_by", pagination.sortBy);
  if (pagination.sortOrder) params.set("sort_order", pagination.sortOrder);
  if (pagination.page) params.set("page", String(pagination.page));
  if (pagination.pageSize) params.set("page_size", String(pagination.pageSize));
  if (counterpartCountryId) params.set("counterpart_country_id", String(counterpartCountryId));
  if (direction) params.set("direction", direction);
  return fetchJson<CountryDetailResponse>(buildUrl(`/countries/${countryId}/detail`, params));
}

export async function fetchClubNetwork(clubId: number, filters: FilterState): Promise<ClubNetworkResponse> {
  return fetchJson<ClubNetworkResponse>(buildUrl(`/clubs/${clubId}/network`, filterParams(filters)));
}

export async function fetchClubNetworkExpand(
  clubId: number,
  countryId: number,
  filters: FilterState,
): Promise<ClubNetworkExpandResponse> {
  return fetchJson<ClubNetworkExpandResponse>(
    buildUrl(`/clubs/${clubId}/network/${countryId}`, filterParams(filters)),
  );
}

export async function searchClubs(query: string, limit = 10): Promise<ClubSearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return fetchJson<ClubSearchResponse>(buildUrl("/clubs/search", params));
}

export async function fetchWindows(): Promise<WindowsResponse> {
  return fetchJson<WindowsResponse>(buildUrl("/filters/windows"));
}

export async function searchPlayers(query: string, limit = 10): Promise<{ players: PlayerSearchResult[] }> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return fetchJson<{ players: PlayerSearchResult[] }>(buildUrl("/players/search", params));
}

export async function fetchPlayerDetail(playerId: number): Promise<PlayerDetail> {
  return fetchJson<PlayerDetail>(buildUrl(`/players/${playerId}`));
}
