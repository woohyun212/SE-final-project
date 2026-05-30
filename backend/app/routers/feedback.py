from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback, FeedbackType
from app.schemas.feedback import LikeDislikeRequest
from app.routers.auth import get_current_user

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/like", status_code=201)
async def like(
    body: LikeDislikeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db.add(Feedback(
        user_id=user.id,
        track_id=body.track_id,
        recommendation_id=body.recommendation_id,
        feedback_type=FeedbackType.like,
    ))
    db.commit()
    return {}


@router.post("/dislike", status_code=201)
async def dislike(
    body: LikeDislikeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db.add(Feedback(
        user_id=user.id,
        track_id=body.track_id,
        recommendation_id=body.recommendation_id,
        feedback_type=FeedbackType.dislike,
    ))
    db.commit()
    return {}
