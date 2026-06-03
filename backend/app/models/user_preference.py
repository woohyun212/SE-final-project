from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

_FEATURE_COLS = ("danceability", "energy", "valence", "acousticness", "instrumentalness")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    like_danceability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    like_energy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    like_valence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    like_acousticness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    like_instrumentalness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    dislike_danceability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dislike_energy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dislike_valence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dislike_acousticness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dislike_instrumentalness: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dislike_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
