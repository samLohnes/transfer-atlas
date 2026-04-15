"""Country model — geographic reference data for map rendering."""

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Country(Base):
    """A football nation with geographic coordinates for map display."""

    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    iso_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    in_scope: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    leagues: Mapped[list["League"]] = relationship(back_populates="country")
    clubs: Mapped[list["Club"]] = relationship(back_populates="country")


from app.models.league import League  # noqa: E402
from app.models.club import Club  # noqa: E402
