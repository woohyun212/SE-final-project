import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.music_catalog import MusicCatalog

_FEATURE_COLS = ("danceability", "energy", "valence", "acousticness", "instrumentalness")


def recommend_by_emotion(
    db: Session,
    emotion_vector: dict[str, float],
    top_k: int = 10,
) -> list[tuple[MusicCatalog, float]]:
    query_vec = np.array([emotion_vector.get(f, 0.5) for f in _FEATURE_COLS], dtype=np.float32)

    # audio features 컬럼과 track_id만 조회 — ORM 객체 전체 로드 불필요
    cols = [getattr(MusicCatalog, f) for f in _FEATURE_COLS]
    rows = db.execute(select(MusicCatalog.track_id, *cols)).all()

    if not rows:
        return []

    track_ids = [r[0] for r in rows]
    matrix = np.array([r[1:] for r in rows], dtype=np.float32)  # shape: (N, 5)

    # 코사인 유사도: (matrix @ query) / (||matrix|| * ||query||)
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0.0:
        sims = np.zeros(len(rows))
    else:
        dot = matrix @ query_vec
        row_norms = np.linalg.norm(matrix, axis=1)
        with np.errstate(invalid="ignore"):
            sims = np.where(row_norms == 0.0, 0.0, dot / (row_norms * query_norm))

    # argpartition으로 top-k 추출 (전체 정렬보다 O(N) 수준)
    k = min(top_k, len(sims))
    if k == len(sims):
        top_indices = np.argsort(sims)[::-1]
    else:
        top_indices = np.argpartition(sims, -k)[-k:]
        top_indices = top_indices[np.argsort(sims[top_indices])[::-1]]

    top_ids = [track_ids[i] for i in top_indices]
    top_scores = [float(sims[i]) for i in top_indices]

    # top-k track_id로만 ORM 객체 재조회
    result_map = {r.track_id: r for r in db.query(MusicCatalog).filter(MusicCatalog.track_id.in_(top_ids)).all()}
    return [
        (result_map[tid], score)
        for tid, score in zip(top_ids, top_scores, strict=True)
        if tid in result_map
    ]
