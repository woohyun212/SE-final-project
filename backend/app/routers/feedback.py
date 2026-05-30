from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback, FeedbackType
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationSession
from app.schemas.feedback import LikeDislikeRequest
from app.routers.auth import get_current_user

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _validate_feedback(body: LikeDislikeRequest, user_id: int, db: Session) -> None:
    session = db.get(RecommendationSession, body.recommendation_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="추천 세션을 찾을 수 없습니다.")
    if db.get(MusicCatalog, body.track_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="트랙을 찾을 수 없습니다.")


@router.post("/like", status_code=201)
async def like(
    body: LikeDislikeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _validate_feedback(body, user.id, db)
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
    _validate_feedback(body, user.id, db)
    db.add(Feedback(
        user_id=user.id,
        track_id=body.track_id,
        recommendation_id=body.recommendation_id,
        feedback_type=FeedbackType.dislike,
    ))
    db.commit()
    return {}
