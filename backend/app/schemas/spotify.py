from pydantic import BaseModel


class AudioFeatures(BaseModel):
    track_id: str
    # include_metadata=False 로 호출 시 메타데이터 없이 반환될 수 있어 Optional
    name: str | None = None
    artists: list[str] | None = None
    album: str | None = None
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
