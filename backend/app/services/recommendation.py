import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.music_catalog import MusicCatalog
from app.models.user_preference import _FEATURE_COLS, UserPreference

_LIKE_WEIGHT = 0.3
_DISLIKE_WEIGHT = 0.3


def _cosine_sims(matrix: np.ndarray, vec: np.ndarray, row_norms: np.ndarray | None = None) -> np.ndarray:
    vec_norm = np.linalg.norm(vec)
    if vec_norm == 0.0:
        return np.zeros(len(matrix))
    if row_norms is None:
        row_norms = np.linalg.norm(matrix, axis=1)
    with np.errstate(invalid="ignore"):
        return np.where(row_norms == 0.0, 0.0, (matrix @ vec) / (row_norms * vec_norm))


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

    # 사용자 프로필 O(1) PK 조회 — 피드백 풀스캔 대체
    if user_id is not None:
        pref = db.get(UserPreference, user_id)
        if pref is not None:
            if pref.like_count > 0:
                like_vec = np.array([getattr(pref, f"like_{f}") for f in _FEATURE_COLS], dtype=np.float32)
                sims = sims + _LIKE_WEIGHT * _cosine_sims(matrix, like_vec, row_norms)
            if pref.dislike_count > 0:
                dislike_vec = np.array([getattr(pref, f"dislike_{f}") for f in _FEATURE_COLS], dtype=np.float32)
                sims = sims - _DISLIKE_WEIGHT * _cosine_sims(matrix, dislike_vec, row_norms)

    sims = np.clip(sims, 0.0, 1.0)

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
