"""Pre-aggregated summary tables for fast API queries."""

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CountryTransferFlow(Base):
    """Aggregated transfer flows between countries per window."""

    __tablename__ = "country_transfer_flows"
    __table_args__ = (
        Index(
            "uq_country_flow",
            "from_country_id", "to_country_id", "transfer_window",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False
    )
    to_country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False
    )
    transfer_window: Mapped[str] = mapped_column(String(20), nullable=False)
    total_fee_eur: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    transfer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    from_country: Mapped["Country"] = relationship(foreign_keys=[from_country_id])
    to_country: Mapped["Country"] = relationship(foreign_keys=[to_country_id])


class ClubTransferSummary(Base):
    """Aggregated transfer summary per club per window."""

    __tablename__ = "club_transfer_summaries"
    __table_args__ = (
        Index("uq_club_summary", "club_id", "transfer_window", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clubs.id", ondelete="RESTRICT"), nullable=False
    )
    transfer_window: Mapped[str] = mapped_column(String(20), nullable=False)
    total_spent_eur: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_received_eur: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    players_bought: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    players_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    club: Mapped["Club"] = relationship()


from app.models.country import Country  # noqa: E402
from app.models.club import Club  # noqa: E402
