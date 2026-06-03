from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationResult, RecommendationSession
from app.routers.auth import get_current_user
from app.schemas.history import FeedbackEntry, HistoryItem, RecommendedTrackEntry

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[HistoryItem])
async def get_history(
    n: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """최근 추천 세션 N개 + 세션별 추천 결과 곡 + 사용자 피드백 목록."""
    sessions = (
        db.query(RecommendationSession)
        .filter(RecommendationSession.user_id == user.id)
        .order_by(RecommendationSession.created_at.desc())
        .limit(n)
        .all()
    )
    if not sessions:
        return []

    session_ids = [s.id for s in sessions]

    # 추천 결과 곡 단일 쿼리 (N+1 회피)
    result_rows = (
        db.query(RecommendationResult, MusicCatalog)
        .outerjoin(MusicCatalog, RecommendationResult.track_id == MusicCatalog.track_id)
        .filter(RecommendationResult.session_id.in_(session_ids))
        .order_by(RecommendationResult.session_id, RecommendationResult.rank)
        .all()
    )

    tracks_by_session: dict[str, list[RecommendedTrackEntry]] = defaultdict(list)
    for result, catalog in result_rows:
        if catalog is None:
            continue
        tracks_by_session[result.session_id].append(
            RecommendedTrackEntry(
                track_id=catalog.track_id,
                title=catalog.track_name,
                artist=catalog.artists,
                rank=result.rank,
                score=round(result.score, 4),
            )
        )

    # 피드백 단일 쿼리 (N+1 회피)
    feedback_rows = (
        db.query(Feedback, MusicCatalog)
        .join(MusicCatalog, Feedback.track_id == MusicCatalog.track_id)
        .filter(Feedback.recommendation_id.in_(session_ids))
        .all()
    )

    feedbacks_by_session: dict[str, list[FeedbackEntry]] = defaultdict(list)
    for feedback, catalog in feedback_rows:
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
            recommended_tracks=tracks_by_session.get(session.id, []),
            feedbacks=feedbacks_by_session.get(session.id, []),
        )
        for session in sessions
    ]
