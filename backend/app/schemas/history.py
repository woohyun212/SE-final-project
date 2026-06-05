from datetime import datetime

from pydantic import BaseModel


class FeedbackEntry(BaseModel):
    track_id: str
    title: str
    artist: str
    feedback_type: str


class RecommendedTrackEntry(BaseModel):
    track_id: str
    title: str
    artist: str
    rank: int
    score: float


class HistoryItem(BaseModel):
    id: str
    user_valence: float
    user_energy: float
    created_at: datetime
    recommended_tracks: list[RecommendedTrackEntry] = []
    feedbacks: list[FeedbackEntry] = []
