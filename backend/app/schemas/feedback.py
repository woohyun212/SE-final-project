from typing import Literal

from pydantic import BaseModel, Field


class LikeDislikeRequest(BaseModel):
    track_id: str
    recommendation_id: str


class PlaybackRequest(BaseModel):
    track_id: str
    event: Literal["start", "end", "complete"]
    playback_pct: float | None = Field(default=None, ge=0.0, le=100.0)
