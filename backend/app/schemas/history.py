from datetime import datetime

from pydantic import BaseModel


class FeedbackEntry(BaseModel):
    track_id: str
    title: str
    artist: str
    feedback_type: str


class HistoryItem(BaseModel):
    id: str
    user_valence: float
    user_energy: float
    created_at: datetime
    feedbacks: list[FeedbackEntry] = []
