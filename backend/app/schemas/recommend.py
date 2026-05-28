from pydantic import BaseModel

from app.schemas.context import ContextResult


class Track(BaseModel):
    track_id: str
    title: str
    artist: str
    album: str
    duration_sec: int
    preview_url: str | None = None


class RecommendResponse(BaseModel):
    tracks: list[Track]
    context: ContextResult | None = None
