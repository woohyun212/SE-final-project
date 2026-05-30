from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationSession
from app.routers.auth import get_current_user
from app.schemas.history import FeedbackEntry, HistoryItem

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryItem])
async def get_history(
    n: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """최근 추천 세션 N개 + 각 세션에서 사용자가 남긴 피드백 트랙 목록."""
    sessions = (
        db.query(RecommendationSession)
        .filter(RecommendationSession.user_id == user.id)
        .order_by(RecommendationSession.created_at.desc())
        .limit(n)
        .all()
    )
    if not sessions:
        return []

    # 세션 전체에 대한 피드백을 단일 쿼리로 조회 (N+1 회피)
    session_ids = [s.id for s in sessions]
    rows = (
        db.query(Feedback, MusicCatalog)
        .join(MusicCatalog, Feedback.track_id == MusicCatalog.track_id)
        .filter(Feedback.recommendation_id.in_(session_ids))
        .all()
    )

    feedbacks_by_session: dict[str, list[FeedbackEntry]] = defaultdict(list)
    for feedback, catalog in rows:
        feedbacks_by_session[feedback.recommendation_id].append(
            FeedbackEntry(
                track_id=catalog.track_id,
                title=catalog.track_name,
                artist=catalog.artists,
                feedback_type=feedback.feedback_type,
            )
        )

    return [
        HistoryItem(
            id=session.id,
            user_valence=session.user_valence,
            user_energy=session.user_energy,
            created_at=session.created_at,
            feedbacks=feedbacks_by_session.get(session.id, []),
        )
        for session in sessions
    ]
