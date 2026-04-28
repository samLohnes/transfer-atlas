"""Print grades for a curated list of transfers and a pass/fail gate.

The list is the release-gate spec defined in the design doc:
docs/superpowers/specs/2026-04-27-initial-release-prep-design.md
At least 8 of 10 must grade B+ (composite >= 78) or higher.
"""

import sys
from dataclasses import dataclass

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Club, Player, Transfer, TransferGrade

# Composite >= 78 = B+ or higher per Phase 2 letter scale.
B_PLUS_THRESHOLD = 78.0
GATE_PASSING_COUNT = 8


@dataclass
class CuratedTransfer:
    label: str
    player_name: str
    to_club_name: str
    year: int


# Player + club names use SUBSTRINGS that match Transfermarkt's actual stored values
# (e.g., "Liverpool Football Club" not "Liverpool FC"; "Rodri" not "Rodri Hernández";
#  "Julián Alvarez" not "Julián Álvarez"). Year + name + club together disambiguate.
CURATED: list[CuratedTransfer] = [
    CuratedTransfer("Rodri → Man City 2019",         "Rodri",          "Manchester City",         2019),
    CuratedTransfer("Kanté → Chelsea 2016",          "Kanté",          "Chelsea Football Club",   2016),
    CuratedTransfer("De Bruyne → Man City 2015",     "De Bruyne",      "Manchester City",         2015),
    CuratedTransfer("Bellingham → Real Madrid 2023", "Bellingham",     "Real Madrid",             2023),
    CuratedTransfer("Van Dijk → Liverpool 2018",     "Van Dijk",       "Liverpool Football Club", 2018),
    CuratedTransfer("Cancelo → Man City 2019",       "Cancelo",        "Manchester City",         2019),
    CuratedTransfer("Alisson → Liverpool 2018",      "Alisson",        "Liverpool Football Club", 2018),
    CuratedTransfer("Haaland → Man City 2022",       "Haaland",        "Manchester City",         2022),
    CuratedTransfer("Salah → Liverpool 2017",        "Salah",          "Liverpool Football Club", 2017),
    CuratedTransfer("Álvarez → Man City 2022",       "Alvarez",        "Manchester City",         2022),
]


def lookup_grade(session: Session, c: CuratedTransfer):
    """Best-effort match by player-name substring + to-club-name substring + transfer year."""
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
    )
    rows = q.all()
    # Year filter applied client-side because transfer_date may be NULL
    rows = [r for r in rows if r[0].transfer_date and r[0].transfer_date.year == c.year]
    return rows[0] if rows else None


def main() -> int:
    session: Session = SessionLocal()
    try:
        passes = 0
        misses: list[str] = []
        print(f"{'PLAYER':<32} {'GRADE':<6} {'COMPOSITE':>10}  STATUS")
        print("-" * 70)
        for c in CURATED:
            hit = lookup_grade(session, c)
            if hit is None:
                print(f"{c.label:<32} {'?':<6} {'—':>10}  NOT FOUND in DB")
                misses.append(c.label + " (not found)")
                continue
            transfer, grade, player, club = hit
            if grade is None:
                print(f"{c.label:<32} {'?':<6} {'—':>10}  TRANSFER UNGRADED (loan/free?)")
                misses.append(c.label + " (no grade)")
                continue
            score = float(grade.composite_score)
            ok = score >= B_PLUS_THRESHOLD
            status = "PASS" if ok else "FAIL"
            print(f"{c.label:<32} {grade.letter_grade:<6} {score:>10.1f}  {status}")
            if ok:
                passes += 1
            else:
                misses.append(f"{c.label} ({grade.letter_grade} {score:.1f})")

        print("-" * 70)
        gate_passed = passes >= GATE_PASSING_COUNT
        print(f"Curated gate: {passes}/{len(CURATED)} >= B+   {'✓ PASSING' if gate_passed else '✗ FAILING'}")
        if misses:
            print("Misses:")
            for m in misses:
                print(f"  - {m}")
        return 0 if gate_passed else 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
