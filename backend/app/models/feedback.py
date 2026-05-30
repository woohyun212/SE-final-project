import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FeedbackType(str, enum.Enum):
    like = "like"
    dislike = "dislike"


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (
        UniqueConstraint("user_id", "track_id", "recommendation_id", name="uq_feedback_user_track_session"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("music_catalog.track_id"), nullable=False)
    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendation_sessions.id"), nullable=False)
    feedback_type: Mapped[FeedbackType] = mapped_column(Enum(FeedbackType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PlaybackEvent(Base):
    __tablename__ = "playback_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("music_catalog.track_id"), nullable=False)
    event: Mapped[str] = mapped_column(String(16), nullable=False)
    playback_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
