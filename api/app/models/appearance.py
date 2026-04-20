"""Appearance model — per-match player statistics sourced from Transfermarkt."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Appearance(Base):
    """A single player's per-match contribution (minutes, goals, assists, cards)."""

    __tablename__ = "appearances"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="uq_appearances_player_game"),
        Index("ix_appearances_player_date", "player_id", "date"),
        Index("ix_appearances_club_date", "club_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    game_id: Mapped[str] = mapped_column(String(50), nullable=False)
    club_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False
    )
    competition_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    minutes_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    player: Mapped["Player"] = relationship()
    club: Mapped["Club"] = relationship()


from app.models.player import Player  # noqa: E402
from app.models.club import Club  # noqa: E402
