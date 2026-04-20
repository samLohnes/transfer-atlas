"""Player model — individual footballers."""

from datetime import date

from sqlalchemy import BigInteger, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Player(Base):
    """A football player with position, nationality, physical profile, and market-value snapshots."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    position: Mapped[str | None] = mapped_column(String(50), nullable=True)
    position_group: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transfermarkt_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )
    transfermarkt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    height_in_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    foot: Mapped[str | None] = mapped_column(String(10), nullable=True)
    international_caps: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    international_goals: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    current_market_value_eur: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    peak_market_value_eur: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    contract_expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
