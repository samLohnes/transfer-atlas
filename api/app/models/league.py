"""League model — competition reference data."""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class League(Base):
    """A football league/competition within a country."""

    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False
    )
    tier: Mapped[int] = mapped_column(Integer, nullable=False)
    transfermarkt_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )

    country: Mapped["Country"] = relationship(back_populates="leagues")
    clubs: Mapped[list["Club"]] = relationship(back_populates="current_league")


from app.models.country import Country  # noqa: E402
from app.models.club import Club  # noqa: E402
