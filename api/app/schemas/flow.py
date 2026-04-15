"""Country transfer flow response schemas."""

from pydantic import BaseModel


class FlowItem(BaseModel):
    """A directional flow between two countries."""

    from_country_id: int
    from_country_name: str
    to_country_id: int
    to_country_name: str
    total_fee_eur: int
    transfer_count: int
    loan_count: int


class CountryFlowSummary(BaseModel):
    """Per-country net spend summary."""

    country_id: int
    country_name: str
    total_spent_eur: int
    total_received_eur: int
    net_spend_eur: int


class CountryFlowsResponse(BaseModel):
    """Full response for the map view."""

    flows: list[FlowItem]
    country_summaries: list[CountryFlowSummary]
