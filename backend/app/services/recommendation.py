import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback, FeedbackType
from app.models.music_catalog import MusicCatalog

_FEATURE_COLS = ("danceability", "energy", "valence", "acousticness", "instrumentalness")
_LIKE_WEIGHT = 0.3     # 좋아요 boost 계수 — boost > penalty로 설정해 탐색 다양성 유지
_DISLIKE_WEIGHT = 0.2  # 싫어요 penalty 계수 — 초기 경험적 값, 추후 A/B 튜닝 예정


def _cosine_sims(matrix: np.ndarray, vec: np.ndarray, row_norms: np.ndarray | None = None) -> np.ndarray:
    vec_norm = np.linalg.norm(vec)
    if vec_norm == 0.0:
        return np.zeros(len(matrix))
    if row_norms is None:
        row_norms = np.linalg.norm(matrix, axis=1)
    with np.errstate(invalid="ignore"):
        return np.where(row_norms == 0.0, 0.0, (matrix @ vec) / (row_norms * vec_norm))


def _user_preference_vectors(
    db: Session, user_id: int
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """사용자 피드백 이력으로 선호/비선호 feature 벡터 반환. 이력 없으면 None."""
    cols = [getattr(MusicCatalog, f) for f in _FEATURE_COLS]
    rows = db.execute(
        select(Feedback.feedback_type, *cols)
        .join(MusicCatalog, MusicCatalog.track_id == Feedback.track_id)
        .where(Feedback.user_id == user_id)
    ).all()

    liked = [list(r[1:]) for r in rows if r[0] == FeedbackType.like]
    disliked = [list(r[1:]) for r in rows if r[0] == FeedbackType.dislike]

    pref_vec = np.mean(liked, axis=0).astype(np.float32) if liked else None
    dislike_vec = np.mean(disliked, axis=0).astype(np.float32) if disliked else None

    return pref_vec, dislike_vec


def recommend_by_emotion(
    db: Session,
    emotion_vector: dict[str, float],
    user_id: int | None = None,
    top_k: int = 10,
) -> list[tuple[MusicCatalog, float]]:
    query_vec = np.array([emotion_vector.get(f, 0.5) for f in _FEATURE_COLS], dtype=np.float32)

    cols = [getattr(MusicCatalog, f) for f in _FEATURE_COLS]
    rows = db.execute(select(MusicCatalog.track_id, *cols)).all()

    if not rows:
        return []

    track_ids = [r[0] for r in rows]
    matrix = np.array([r[1:] for r in rows], dtype=np.float32)  # shape: (N, 5)

    row_norms = np.linalg.norm(matrix, axis=1)
    sims = _cosine_sims(matrix, query_vec, row_norms)

    # 누적 피드백 가중치 반영 (cold start: user_id=None 또는 이력 없으면 건너뜀)
    if user_id is not None:
        pref_vec, dislike_vec = _user_preference_vectors(db, user_id)
        if pref_vec is not None:
            sims = sims + _LIKE_WEIGHT * _cosine_sims(matrix, pref_vec, row_norms)
        if dislike_vec is not None:
            sims = sims - _DISLIKE_WEIGHT * _cosine_sims(matrix, dislike_vec, row_norms)
        sims = np.clip(sims, 0.0, None)

    k = min(top_k, len(sims))
    if k == len(sims):
        top_indices = np.argsort(sims)[::-1]
    else:
        top_indices = np.argpartition(sims, -k)[-k:]
        top_indices = top_indices[np.argsort(sims[top_indices])[::-1]]

    top_ids = [track_ids[i] for i in top_indices]
    top_scores = [float(sims[i]) for i in top_indices]

    result_map = {r.track_id: r for r in db.query(MusicCatalog).filter(MusicCatalog.track_id.in_(top_ids)).all()}
    return [
        (result_map[tid], score)
        for tid, score in zip(top_ids, top_scores, strict=True)
        if tid in result_map
    ]
