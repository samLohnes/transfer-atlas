"""Club model — football clubs tracked across leagues."""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Club(Base):
    """A football club with country and league associations."""

    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    current_league_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("leagues.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    transfermarkt_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )
    transfermarkt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    country: Mapped["Country"] = relationship(back_populates="clubs")
    current_league: Mapped["League | None"] = relationship(back_populates="clubs")


from app.models.country import Country  # noqa: E402
from app.models.league import League  # noqa: E402
