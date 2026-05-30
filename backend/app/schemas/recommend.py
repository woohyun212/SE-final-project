from pydantic import BaseModel

from app.schemas.context import ContextResult


class TrackInfo(BaseModel):
    track_id: str
    title: str
    artist: str
    album: str
    duration_sec: int
    preview_url: str | None = None


class EmotionVector(BaseModel):
    valence: float
    energy: float


class RecommendationItem(BaseModel):
    recommendation_id: str
    track: TrackInfo
    score: float
    reason: str | None = None
    emotion_vector: EmotionVector


class UserEmotion(BaseModel):
    valence: float
    energy: float


class RecommendResponse(BaseModel):
    recommendations: list[RecommendationItem]
    user_emotion: UserEmotion
    transcript: str | None = None
    context: ContextResult | None = None
