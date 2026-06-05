from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback, FeedbackType, PlaybackEvent
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationSession
from app.models.user_preference import _FEATURE_COLS, UserPreference
from app.routers.auth import get_current_user
from app.schemas.feedback import LikeDislikeRequest, PlaybackRequest

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _validate_feedback(body: LikeDislikeRequest, user_id: int, db: Session) -> MusicCatalog:
    session = db.get(RecommendationSession, body.recommendation_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="추천 세션을 찾을 수 없습니다.")
    track = db.get(MusicCatalog, body.track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="트랙을 찾을 수 없습니다.")
    return track


def _upsert_preference(db: Session, user_id: int, track: MusicCatalog, feedback_type: FeedbackType) -> None:
    pref = db.get(UserPreference, user_id)
    if pref is None:
        pref = UserPreference(
            user_id=user_id,
            like_danceability=0.0, like_energy=0.0, like_valence=0.0,
            like_acousticness=0.0, like_instrumentalness=0.0, like_count=0,
            dislike_danceability=0.0, dislike_energy=0.0, dislike_valence=0.0,
            dislike_acousticness=0.0, dislike_instrumentalness=0.0, dislike_count=0,
        )
        db.add(pref)

    track_vec = [getattr(track, f) for f in _FEATURE_COLS]

    if feedback_type == FeedbackType.like:
        old_count = pref.like_count
        new_count = old_count + 1
        for f, v in zip(_FEATURE_COLS, track_vec, strict=True):
            old_mean = getattr(pref, f"like_{f}")
            setattr(pref, f"like_{f}", old_mean + (v - old_mean) / new_count)
        pref.like_count = new_count
    else:
        old_count = pref.dislike_count
        new_count = old_count + 1
        for f, v in zip(_FEATURE_COLS, track_vec, strict=True):
            old_mean = getattr(pref, f"dislike_{f}")
            setattr(pref, f"dislike_{f}", old_mean + (v - old_mean) / new_count)
        pref.dislike_count = new_count


def _record_feedback(body: LikeDislikeRequest, user_id: int, feedback_type: FeedbackType, db: Session) -> None:
    track = _validate_feedback(body, user_id, db)
    db.add(Feedback(
        user_id=user_id,
        track_id=body.track_id,
        recommendation_id=body.recommendation_id,
        feedback_type=feedback_type,
    ))
    _upsert_preference(db, user_id, track, feedback_type)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 피드백을 남긴 트랙입니다."
        ) from None


@router.post("/like", status_code=201)
async def like(
    body: LikeDislikeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _record_feedback(body, user.id, FeedbackType.like, db)
    return {}


@router.post("/dislike", status_code=201)
async def dislike(
    body: LikeDislikeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _record_feedback(body, user.id, FeedbackType.dislike, db)
    return {}


@router.post("/playback", status_code=201)
async def playback(
    body: PlaybackRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if db.get(MusicCatalog, body.track_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="트랙을 찾을 수 없습니다.")
    db.add(PlaybackEvent(
        user_id=user.id,
        track_id=body.track_id,
        event=body.event,
        playback_pct=body.playback_pct,
    ))
    db.commit()
    return {}
