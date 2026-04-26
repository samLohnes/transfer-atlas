"""Service layer for the grading endpoints + grade enrichment of existing endpoints.

Pulls TransferGrade rows, joins them to Transfer/Player/Club/Country/ScoringVersion
context, and builds the response shapes defined in `app/schemas/grade.py`.

Re-exports `build_grade_brief()` for use in the existing country/player/club_service
modules so the LEFT JOIN-driven enrichment stays consistent across endpoints.
"""

from collections import Counter
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.models import (
    Club, Country, Player, ScoringVersion, Transfer, TransferFeature, TransferGrade,
)
from app.schemas.grade import (
    ClubBestWorst, ClubReportCard, ClubTimeline, GradeBrief, GradeComponent,
    GradeDetail, PlayerGradeSummary, RankedTransfer,
)
from app.services.windows import get_windows_in_range, window_sort_key
from ml.explain import generate_summary_line
from ml.utils import derive_letter_grade

# Used to omit NULL components from /transfers/{id}/grade responses.
COMPONENT_FIELDS = ("minutes", "production", "value_trajectory", "financial_return")


# ---------------------------------------------------------------------------
# Helpers used by both the new endpoints and the enriched existing endpoints
# ---------------------------------------------------------------------------


def build_grade_brief(grade: TransferGrade | None) -> GradeBrief | None:
    """Compact grade payload embedded in transfer rows by the existing endpoints."""
    if grade is None:
        return None
    return GradeBrief(
        composite_score=float(grade.composite_score),
        letter_grade=grade.letter_grade,
        worth_the_fee=grade.worth_the_fee,
        is_complete=grade.is_complete,
    )


def fetch_grade_briefs_for_transfers(
    db: Session, transfer_ids: list[int],
) -> dict[int, GradeBrief]:
    """Bulk-fetch grade briefs keyed by transfer_id.

    Used by the existing services to attach `grade` to many transfer rows in one
    indexed query rather than per-row.
    """
    if not transfer_ids:
        return {}
    rows = (
        db.query(TransferGrade)
        .filter(TransferGrade.transfer_id.in_(transfer_ids))
        .all()
    )
    return {r.transfer_id: build_grade_brief(r) for r in rows}


# ---------------------------------------------------------------------------
# GET /transfers/{transfer_id}/grade
# ---------------------------------------------------------------------------


def get_transfer_grade_detail(db: Session, transfer_id: int) -> GradeDetail | None:
    """Returns the full grade for a transfer, or None if no TransferGrade exists.

    The router translates the None case into either 404 (transfer doesn't exist)
    or 204 (transfer exists but isn't gradeable) by checking Transfer separately.
    """
    row = (
        db.query(TransferGrade, ScoringVersion.version)
        .join(ScoringVersion, TransferGrade.scoring_version_id == ScoringVersion.id)
        .filter(TransferGrade.transfer_id == transfer_id)
        .first()
    )
    if row is None:
        return None

    grade, version = row
    components: dict[str, GradeComponent] = {}
    score_pairs = (
        ("minutes", grade.minutes_score, grade.minutes_explanation),
        ("production", grade.production_score, grade.production_explanation),
        ("value_trajectory", grade.value_trajectory_score, grade.value_trajectory_explanation),
        ("financial_return", grade.financial_return_score, grade.financial_return_explanation),
    )
    for name, score, explanation in score_pairs:
        if score is None:
            continue
        components[name] = GradeComponent(
            score=float(score),
            explanation=explanation or "",
        )

    return GradeDetail(
        transfer_id=grade.transfer_id,
        composite_score=float(grade.composite_score),
        letter_grade=grade.letter_grade,
        worth_the_fee=grade.worth_the_fee,
        is_complete=grade.is_complete,
        components=components,
        model_version=version,
        graded_at=grade.graded_at,
    )


# ---------------------------------------------------------------------------
# GET /grades/top
# ---------------------------------------------------------------------------


def get_top_grades(
    db: Session,
    *,
    category: str = "best",
    limit: int = 10,
    offset: int = 0,
    position_group: str | None = None,
    country_id: int | None = None,
    fee_min: int | None = None,
    fee_max: int | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
    completed_only: bool = True,
) -> tuple[list[RankedTransfer], int]:
    """Return the (rankings, total) tuple for the best/worst rankings page.

    `total` is the count of rows matching the filters before LIMIT/OFFSET, so
    the frontend can drive paging UI.
    """
    FromClub = aliased(Club, name="from_club")
    ToClub = aliased(Club, name="to_club")
    ToCountry = aliased(Country, name="to_country")

    base = (
        db.query(
            TransferGrade,
            Transfer,
            TransferFeature,
            Player.id.label("player_id"),
            Player.name.label("player_name"),
            Player.position_group.label("player_position_group"),
            FromClub.name.label("from_club_name"),
            ToClub.name.label("to_club_name"),
            ToCountry.name.label("to_club_country"),
        )
        .join(Transfer, TransferGrade.transfer_id == Transfer.id)
        .outerjoin(TransferFeature, TransferFeature.transfer_id == Transfer.id)
        .join(Player, Transfer.player_id == Player.id)
        .join(FromClub, Transfer.from_club_id == FromClub.id)
        .join(ToClub, Transfer.to_club_id == ToClub.id)
        .join(ToCountry, ToClub.country_id == ToCountry.id)
    )

    if completed_only:
        base = base.filter(TransferGrade.is_complete.is_(True))
    if position_group:
        base = base.filter(Player.position_group == position_group)
    if country_id is not None:
        base = base.filter(ToClub.country_id == country_id)
    if fee_min is not None:
        base = base.filter(Transfer.fee_eur >= fee_min)
    if fee_max is not None:
        base = base.filter(Transfer.fee_eur <= fee_max)
    if window_start or window_end:
        all_windows = [r[0] for r in db.query(Transfer.transfer_window).distinct().all()]
        windows = get_windows_in_range(all_windows, window_start, window_end)
        if windows is not None:
            base = base.filter(Transfer.transfer_window.in_(windows))

    total = base.count()

    if category == "worst":
        base = base.order_by(TransferGrade.composite_score.asc())
    else:
        base = base.order_by(TransferGrade.composite_score.desc())

    rows = base.offset(offset).limit(limit).all()

    out: list[RankedTransfer] = []
    for grade, transfer, feature, player_id, player_name, player_pg, from_name, to_name, to_country in rows:
        out.append(RankedTransfer(
            transfer_id=grade.transfer_id,
            player_name=player_name,
            player_id=player_id,
            from_club_name=from_name,
            to_club_name=to_name,
            to_club_country=to_country,
            fee_eur=int(transfer.fee_eur or 0),
            composite_score=float(grade.composite_score),
            letter_grade=grade.letter_grade,
            worth_the_fee=grade.worth_the_fee,
            is_complete=grade.is_complete,
            transfer_window=transfer.transfer_window,
            position_group=player_pg,
            summary=_compute_summary_line(grade, feature),
        ))

    return out, total


def _compute_summary_line(grade: TransferGrade, feature: TransferFeature | None) -> str:
    """Generate the one-line ranking summary on the fly from grade + feature data."""
    if feature is None:
        return "Insufficient data"
    return generate_summary_line(
        is_complete=grade.is_complete,
        minutes_score=_to_float(grade.minutes_score),
        production_score=_to_float(grade.production_score),
        value_trajectory_score=_to_float(grade.value_trajectory_score),
        financial_return_score=_to_float(grade.financial_return_score),
        minutes_pct=feature.minutes_pct,
        goals=feature.goals,
        assists=feature.assists,
        value_change_pct=feature.value_change_pct,
        exit_fee_ratio=feature.exit_fee_ratio,
        tenure_days=feature.tenure_days,
    )


def _to_float(value) -> float | None:
    if value is None:
        return None
    return float(value)


# ---------------------------------------------------------------------------
# GET /grades/club-comparison
# ---------------------------------------------------------------------------


def get_club_comparison(
    db: Session,
    club_ids: list[int],
    window_start: str | None = None,
    window_end: str | None = None,
) -> list[ClubReportCard]:
    """Build the report card for each requested club. Validation (1-3 ids) lives in the router."""
    out: list[ClubReportCard] = []

    windows: list[str] | None = None
    if window_start or window_end:
        all_windows = [r[0] for r in db.query(Transfer.transfer_window).distinct().all()]
        windows = get_windows_in_range(all_windows, window_start, window_end)

    for club_id in club_ids:
        club = db.query(Club).filter(Club.id == club_id).first()
        if club is None:
            # Skip silently — frontend will simply see one fewer card. Matches
            # the existing `clubs/network` behaviour where a missing club
            # short-circuits to an empty edge list.
            continue

        q = (
            db.query(TransferGrade, Transfer, Player.name.label("player_name"))
            .join(Transfer, TransferGrade.transfer_id == Transfer.id)
            .join(Player, Transfer.player_id == Player.id)
            .filter(Transfer.to_club_id == club_id)
        )
        if windows is not None:
            q = q.filter(Transfer.transfer_window.in_(windows))
        rows = q.all()

        if not rows:
            out.append(ClubReportCard(
                club_id=club.id,
                club_name=club.name,
                overall_average_grade=0.0,
                overall_letter_grade="F",
                total_graded_transfers=0,
                total_spend_eur=0,
                best_transfer=None,
                worst_transfer=None,
                grade_distribution={g: 0 for g in ("A", "B+", "B", "C+", "C", "D", "F")},
                timeline=[],
            ))
            continue

        composite_values = [float(g.composite_score) for g, _, _ in rows]
        avg = sum(composite_values) / len(composite_values)
        spend = sum(int(t.fee_eur or 0) for _, t, _ in rows)

        best_row = max(rows, key=lambda r: r[0].composite_score)
        worst_row = min(rows, key=lambda r: r[0].composite_score)
        best = ClubBestWorst(
            transfer_id=best_row[0].transfer_id,
            player_name=best_row[2],
            composite_score=float(best_row[0].composite_score),
            letter_grade=best_row[0].letter_grade,
            fee_eur=int(best_row[1].fee_eur or 0),
        )
        worst = ClubBestWorst(
            transfer_id=worst_row[0].transfer_id,
            player_name=worst_row[2],
            composite_score=float(worst_row[0].composite_score),
            letter_grade=worst_row[0].letter_grade,
            fee_eur=int(worst_row[1].fee_eur or 0),
        )

        distribution = Counter(g.letter_grade for g, _, _ in rows)
        full_distribution = {grade: distribution.get(grade, 0) for grade in (
            "A", "B+", "B", "C+", "C", "D", "F",
        )}

        # Timeline: average grade per transfer window, ordered chronologically
        per_window: dict[str, list[float]] = {}
        for g, t, _ in rows:
            per_window.setdefault(t.transfer_window, []).append(float(g.composite_score))
        timeline = [
            ClubTimeline(
                transfer_window=window,
                average_grade=sum(scores) / len(scores),
                transfer_count=len(scores),
            )
            for window, scores in sorted(per_window.items(), key=lambda kv: window_sort_key(kv[0]))
        ]

        out.append(ClubReportCard(
            club_id=club.id,
            club_name=club.name,
            overall_average_grade=avg,
            overall_letter_grade=derive_letter_grade(Decimal(str(avg))),
            total_graded_transfers=len(rows),
            total_spend_eur=spend,
            best_transfer=best,
            worst_transfer=worst,
            grade_distribution=full_distribution,
            timeline=timeline,
        ))

    return out


# ---------------------------------------------------------------------------
# GET /grades/scoring-info
# ---------------------------------------------------------------------------


def get_scoring_info(db: Session) -> dict | None:
    """Return active ScoringVersion fields + computed grade_distribution.

    Returns None when no active version exists (the grading pipeline hasn't run).
    """
    active = db.query(ScoringVersion).filter(ScoringVersion.is_active.is_(True)).first()
    if active is None:
        return None

    distribution_rows = (
        db.query(TransferGrade.letter_grade, func.count())
        .group_by(TransferGrade.letter_grade)
        .all()
    )
    distribution = {grade: count for grade, count in distribution_rows}
    full_distribution = {g: distribution.get(g, 0) for g in (
        "A", "B+", "B", "C+", "C", "D", "F",
    )}

    return {
        "version": active.version,
        "scored_at": active.scored_at,
        "total_scored": active.total_scored,
        "component_weights": active.component_weights,
        "calibrated_rates": active.calibrated_rates,
        "grade_distribution": full_distribution,
    }


# ---------------------------------------------------------------------------
# Player grade summary (used by the existing players router)
# ---------------------------------------------------------------------------


def get_grade_summary_for_player(db: Session, player_id: int) -> PlayerGradeSummary | None:
    """Aggregate stats over the player's incoming-transfer grades.

    Per spec: only consider transfers where the player was the *incoming* side
    (Transfer.player_id == player_id). Returns None when the player has no
    graded transfers.
    """
    rows = (
        db.query(TransferGrade, Transfer)
        .join(Transfer, TransferGrade.transfer_id == Transfer.id)
        .filter(Transfer.player_id == player_id)
        .all()
    )
    if not rows:
        return None

    composite_values = [float(g.composite_score) for g, _ in rows]
    avg = sum(composite_values) / len(composite_values)

    best_row = max(rows, key=lambda r: r[0].composite_score)
    worst_row = min(rows, key=lambda r: r[0].composite_score)
    best = ClubBestWorst(
        transfer_id=best_row[0].transfer_id,
        player_name="",  # not needed in the player's own summary
        composite_score=float(best_row[0].composite_score),
        letter_grade=best_row[0].letter_grade,
        fee_eur=int(best_row[1].fee_eur or 0),
    )
    worst = ClubBestWorst(
        transfer_id=worst_row[0].transfer_id,
        player_name="",
        composite_score=float(worst_row[0].composite_score),
        letter_grade=worst_row[0].letter_grade,
        fee_eur=int(worst_row[1].fee_eur or 0),
    )

    return PlayerGradeSummary(
        average_grade=avg,
        total_graded_transfers=len(rows),
        best_grade=best,
        worst_grade=worst,
    )
