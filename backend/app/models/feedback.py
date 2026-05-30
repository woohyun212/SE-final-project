import enum
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FeedbackType(str, enum.Enum):
    like = "like"
    dislike = "dislike"


class Feedback(Base):
    __tablename__ = "feedbacks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("music_catalog.track_id"), nullable=False)
    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendation_sessions.id"), nullable=False)
    feedback_type: Mapped[FeedbackType] = mapped_column(Enum(FeedbackType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
