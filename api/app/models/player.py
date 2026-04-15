"""Player model — individual footballers."""

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Player(Base):
    """A football player with position and nationality data."""

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
