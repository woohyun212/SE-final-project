from pydantic import BaseModel


class Track(BaseModel):
    title: str
    artist: str
    album: str
    duration_sec: int
    track_id: str | None = None
    preview_url: str | None = None


class RecommendResponse(BaseModel):
    tracks: list[Track]
