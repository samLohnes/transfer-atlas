"""Transfer model — player movements between clubs."""

from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transfer(Base):
    """A completed player transfer or loan between two clubs."""

    __tablename__ = "transfers"
    __table_args__ = (
        Index("ix_transfers_window", "transfer_window"),
        Index("ix_transfers_from_to_window", "from_club_id", "to_club_id", "transfer_window"),
        Index(
            "uq_transfers_natural_key",
            "player_id", "transfer_date", "from_club_id", "to_club_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    from_club_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    to_club_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    fee_eur: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fee_is_loan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_window: Mapped[str] = mapped_column(String(20), nullable=False)
    transfer_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    season: Mapped[str] = mapped_column(String(9), nullable=False)

    player: Mapped["Player"] = relationship()
    from_club: Mapped["Club"] = relationship(foreign_keys=[from_club_id])
    to_club: Mapped["Club"] = relationship(foreign_keys=[to_club_id])


from app.models.player import Player  # noqa: E402
from app.models.club import Club  # noqa: E402
