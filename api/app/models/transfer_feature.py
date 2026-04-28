"""TransferFeature model — pre-computed features feeding the scoring pipeline."""

from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TransferFeature(Base):
    """One row per qualifying transfer. Snapshot of minutes, production, value, and financial features."""

    __tablename__ = "transfer_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transfer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transfers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tenure_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_appearances: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals_per_90: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    assists_per_90: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    goal_contributions_per_90: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 3), nullable=True
    )
    position_group: Mapped[str | None] = mapped_column(String(3), nullable=True)
    position_subgroup: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)
    fee_percentile: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    entry_fee_eur: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    exit_fee_eur: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    age_at_transfer: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    age_at_departure: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    value_at_transfer: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    peak_value_during_stint: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    value_at_departure: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    value_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 2), nullable=True)
    exit_fee_ratio: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    expected_exit_ratio: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    exit_ratio_vs_expected: Mapped[Decimal | None] = mapped_column(
        Numeric(7, 4), nullable=True
    )
    international_caps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    transfer: Mapped["Transfer"] = relationship()


from app.models.transfer import Transfer  # noqa: E402
