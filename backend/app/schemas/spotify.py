from pydantic import BaseModel


class AudioFeatures(BaseModel):
    track_id: str
    name: str
    artists: list[str]
    album: str
    duration_ms: int
    danceability: float
    energy: float
    key: int
    loudness: float
    mode: int
    speechiness: float
    acousticness: float
    instrumentalness: float
    liveness: float
    valence: float
    tempo: float


class TrackSearchResult(BaseModel):
    track_id: str
    name: str
    artists: list[str]
    album: str
    duration_ms: int
    preview_url: str | None = None


class TrackSearchResponse(BaseModel):
    tracks: list[TrackSearchResult]
    total: int
