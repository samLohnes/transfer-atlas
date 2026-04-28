"""PlayerValuation model — historical market values."""

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PlayerValuation(Base):
    """A point-in-time market valuation for a player."""

    __tablename__ = "player_valuations"
    __table_args__ = (
        UniqueConstraint("player_id", "valuation_date", name="uq_player_valuations_player_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    valuation_eur: Mapped[int] = mapped_column(BigInteger, nullable=False)
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False)

    player: Mapped["Player"] = relationship()


from app.models.player import Player  # noqa: E402
