from pydantic import BaseModel


class Track(BaseModel):
    title: str
    artist: str
    album: str
    duration_sec: int


class RecommendResponse(BaseModel):
    tracks: list[Track]
