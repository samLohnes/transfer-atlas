"""Grade-related response schemas.

`GradeBrief` is the abbreviated form embedded in transfer rows across the existing
endpoints. `GradeDetail` is the full breakdown returned by `/transfers/{id}/grade`
on hover. The other classes back the new `/grades/*` endpoints.
"""

from datetime import datetime

from pydantic import BaseModel


class GradeBrief(BaseModel):
    """Abbreviated grade attached to transfer rows in country/player/network endpoints."""

    composite_score: float
    letter_grade: str
    worth_the_fee: bool
    is_complete: bool


class GradeComponent(BaseModel):
    """One of the four scoring components in the breakdown tooltip."""

    score: float
    explanation: str


class GradeDetail(BaseModel):
    """Full grade with per-component scores + explanations + version metadata."""

    transfer_id: int
    composite_score: float
    letter_grade: str
    worth_the_fee: bool
    is_complete: bool
    components: dict[str, GradeComponent]
    model_version: str
    graded_at: datetime


class RankedTransfer(BaseModel):
    """One row in the best/worst rankings list."""

    transfer_id: int
    player_name: str
    player_id: int
    from_club_name: str
    to_club_name: str
    to_club_country: str
    fee_eur: int
    composite_score: float
    letter_grade: str
    worth_the_fee: bool
    is_complete: bool
    transfer_window: str
    position_group: str | None
    summary: str


class TopGradesResponse(BaseModel):
    """Paginated rankings response."""

    category: str
    total: int
    transfers: list[RankedTransfer]


class ClubBestWorst(BaseModel):
    """Single best- or worst-graded transfer for a club's report card."""

    transfer_id: int
    player_id: int
    player_name: str
    composite_score: float
    letter_grade: str
    fee_eur: int


class ClubTimeline(BaseModel):
    """One point in a club's grade-over-time line chart."""

    transfer_window: str
    average_grade: float
    transfer_count: int


class ClubReportCard(BaseModel):
    """Per-club aggregate grade statistics for the comparison view."""

    club_id: int
    club_name: str
    overall_average_grade: float
    overall_letter_grade: str
    total_graded_transfers: int
    total_spend_eur: int
    best_transfer: ClubBestWorst | None
    worst_transfer: ClubBestWorst | None
    grade_distribution: dict[str, int]
    timeline: list[ClubTimeline]


class ClubComparisonResponse(BaseModel):
    """Up to 3 clubs' report cards side-by-side."""

    clubs: list[ClubReportCard]


class ScoringInfoResponse(BaseModel):
    """Active scoring configuration + grade-distribution snapshot for diagnostics."""

    version: str
    scored_at: datetime
    total_scored: int
    component_weights: dict[str, float]
    calibrated_rates: dict[str, dict[str, float]]
    grade_distribution: dict[str, int]


class PlayerGradeSummary(BaseModel):
    """Aggregated grade summary attached to a Player detail response."""

    average_grade: float
    total_graded_transfers: int
    best_grade: ClubBestWorst | None
    worst_grade: ClubBestWorst | None
