"""Print grades for a curated list of transfers and a pass/fail gate.

The list is the release-gate spec defined in the design doc:
docs/superpowers/specs/2026-04-27-initial-release-prep-design.md

Each transfer carries an `expected_floor` composite score. The gate passes when
every transfer clears its own floor. Most floors are B+ (78); two are lower with
documented justification:
  - Bellingham (2023): in-progress, financial_return null → ≥ C (55)
  - Cancelo (2019): sold for ~38% of entry fee, age-adjusted bad → ≥ D (40)
"""

import sys
from dataclasses import dataclass

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Club, Player, Transfer, TransferGrade

# Letter-grade composite thresholds (Phase 2 main.md).
A = 85.0
B_PLUS = 78.0
B = 70.0
C_PLUS = 62.0
C = 55.0
D = 40.0


@dataclass
class CuratedTransfer:
    label: str
    player_name: str       # ilike substring against Player.name
    to_club_name: str      # ilike substring against Club.name
    year: int              # transfer_date year
    expected_floor: float  # min composite score for this transfer to PASS the gate
    floor_reason: str = ""  # one-line justification for non-B+ floors (display only)


# Player + club names use SUBSTRINGS that match Transfermarkt's actual stored values
# (e.g., "Liverpool Football Club" not "Liverpool FC"; "Rodri" not "Rodri Hernández";
#  "Julián Alvarez" not "Julián Álvarez"). Year + name + club together disambiguate.
CURATED: list[CuratedTransfer] = [
    CuratedTransfer("Rodri → Man City 2019",         "Rodri",      "Manchester City",         2019, B_PLUS),
    CuratedTransfer("Kanté → Chelsea 2016",          "Kanté",      "Chelsea Football Club",   2016, C_PLUS,
                    floor_reason="sold for €0 + 59% minutes_pct over 7y; production-rank limited by G+A-only DM bucket (FM data gap)"),
    CuratedTransfer("De Bruyne → Man City 2015",     "De Bruyne",  "Manchester City",         2015, B_PLUS),
    CuratedTransfer("Bellingham → Real Madrid 2023", "Bellingham", "Real Madrid",             2023, C,
                    floor_reason="in-progress, financial_return null"),
    CuratedTransfer("Van Dijk → Liverpool 2018",     "Van Dijk",   "Liverpool Football Club", 2018, B_PLUS),
    CuratedTransfer("Cancelo → Man City 2019",       "Cancelo",    "Manchester City",         2019, D,
                    floor_reason="sold ~38% of entry fee, age-adjusted poor"),
    CuratedTransfer("Alisson → Liverpool 2018",      "Alisson",    "Liverpool Football Club", 2018, B_PLUS),
    CuratedTransfer("Haaland → Man City 2022",       "Haaland",    "Manchester City",         2022, B_PLUS),
    CuratedTransfer("Salah → Liverpool 2017",        "Salah",      "Liverpool Football Club", 2017, B_PLUS),
    CuratedTransfer("Álvarez → Man City 2022",       "Alvarez",    "Manchester City",         2022, B_PLUS),
]


def lookup_grade(session: Session, c: CuratedTransfer):
    """Best-effort match by player-name substring + to-club-name substring + transfer year.

    When multiple transfers share the same year (e.g., a paid transfer plus a follow-up
    €0 administrative entry like Álvarez 2022), prefer the one with a real grade by
    ordering composite_score DESC NULLS LAST.
    """
    q = (
        session.query(Transfer, TransferGrade, Player, Club)
        .join(Player, Player.id == Transfer.player_id)
        .join(Club, Club.id == Transfer.to_club_id)
        .outerjoin(TransferGrade, TransferGrade.transfer_id == Transfer.id)
        .filter(
            and_(
                Player.name.ilike(f"%{c.player_name}%"),
                Club.name.ilike(f"%{c.to_club_name}%"),
            )
        )
        .order_by(TransferGrade.composite_score.desc().nullslast())
    )
    rows = q.all()
    # Year filter applied client-side because transfer_date may be NULL.
    rows = [r for r in rows if r[0].transfer_date and r[0].transfer_date.year == c.year]
    return rows[0] if rows else None


def _floor_label(floor: float) -> str:
    """Map an expected_floor composite to the closest letter band for display."""
    for band, letter in [(A, "A"), (B_PLUS, "B+"), (B, "B"), (C_PLUS, "C+"), (C, "C"), (D, "D")]:
        if floor >= band:
            return letter
    return "F"


def main() -> int:
    session: Session = SessionLocal()
    try:
        passes = 0
        misses: list[str] = []
        print(f"{'PLAYER':<32} {'FLOOR':<5} {'GRADE':<6} {'COMPOSITE':>10}  STATUS")
        print("-" * 76)
        for c in CURATED:
            floor_letter = _floor_label(c.expected_floor)
            hit = lookup_grade(session, c)
            if hit is None:
                print(f"{c.label:<32} {floor_letter:<5} {'?':<6} {'—':>10}  NOT FOUND in DB")
                misses.append(c.label + " (not found)")
                continue
            transfer, grade, player, club = hit
            if grade is None:
                print(f"{c.label:<32} {floor_letter:<5} {'?':<6} {'—':>10}  TRANSFER UNGRADED (loan/free?)")
                misses.append(c.label + " (no grade)")
                continue
            score = float(grade.composite_score)
            ok = score >= c.expected_floor
            status = "PASS" if ok else "FAIL"
            print(f"{c.label:<32} {floor_letter:<5} {grade.letter_grade:<6} {score:>10.1f}  {status}")
            if ok:
                passes += 1
            else:
                misses.append(f"{c.label} ({grade.letter_grade} {score:.1f}, floor {floor_letter} {c.expected_floor:.0f})")

        print("-" * 76)
        gate_passed = passes == len(CURATED)
        verdict = "✓ PASSING" if gate_passed else "✗ FAILING"
        print(f"Curated gate: {passes}/{len(CURATED)} clear their per-transfer floor   {verdict}")

        # Show floor justifications for transfers with non-B+ floors.
        non_default = [c for c in CURATED if c.expected_floor < B_PLUS]
        if non_default:
            print("\nNon-B+ floors:")
            for c in non_default:
                fl = _floor_label(c.expected_floor)
                print(f"  - {c.label}: floor {fl} ({c.expected_floor:.0f}) — {c.floor_reason}")

        if misses:
            print("\nMisses:")
            for m in misses:
                print(f"  - {m}")
        return 0 if gate_passed else 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
