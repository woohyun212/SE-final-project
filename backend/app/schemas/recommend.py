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
    track: TrackInfo
    score: float
    reason: str | None = None
    track_features: EmotionVector


class FallbackFlags(BaseModel):
    stt: bool = False
    ml: bool = False
    context: bool = False
    reason: bool = False


class RecommendResponse(BaseModel):
    session_id: str
    recommendations: list[RecommendationItem]
    user_emotion: EmotionVector
    transcript: str | None = None
    context: ContextResult | None = None
    fallback_flags: FallbackFlags = FallbackFlags()
