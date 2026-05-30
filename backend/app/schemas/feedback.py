from pydantic import BaseModel


class LikeDislikeRequest(BaseModel):
    track_id: str
    recommendation_id: str
