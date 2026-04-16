"""Shared filter parameter schemas."""

from dataclasses import dataclass

from fastapi import Query


@dataclass
class TransferFilters:
    """Shared filter parameters for all data endpoints."""

    window_start: str | None = Query(None, description="Start of time range, e.g. 'Summer 2019'")
    window_end: str | None = Query(None, description="End of time range, e.g. 'Winter 2023'")
    transfer_type: str = Query("all", description="'paid', 'free', or 'all'")
    fee_min: int = Query(0, description="Minimum fee in EUR cents")
    fee_max: int | None = Query(None, description="Maximum fee in EUR cents (null = no limit)")
    position_group: str | None = Query(None, description="Comma-separated: GK, DEF, MID, FWD")
    age_min: int | None = Query(None, description="Minimum player age at transfer")
    age_max: int | None = Query(None, description="Maximum player age at transfer")
    country_ids: str | None = Query(None, description="Comma-separated country IDs to filter flows involving these countries")

    @property
    def country_id_list(self) -> list[int] | None:
        """Parse comma-separated country_ids into a list of ints."""
        if not self.country_ids:
            return None
        try:
            return [int(c.strip()) for c in self.country_ids.split(",") if c.strip()]
        except ValueError:
            return None

    @property
    def position_groups(self) -> list[str] | None:
        """Parse comma-separated position_group into a list."""
        if not self.position_group:
            return None
        return [pg.strip().upper() for pg in self.position_group.split(",") if pg.strip()]

    @property
    def needs_player_join(self) -> bool:
        """Whether these filters require joining through the Player table."""
        return self.position_groups is not None or self.age_min is not None or self.age_max is not None

    @property
    def needs_raw_transfers(self) -> bool:
        """Whether these filters require querying raw Transfer rows instead of pre-aggregated tables."""
        return (
            self.needs_player_join
            or self.fee_min > 0
            or self.fee_max is not None
            or self.transfer_type != "all"
        )
