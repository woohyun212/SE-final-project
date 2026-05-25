import math
from sqlalchemy.orm import Session

from app.models.music_catalog import MusicCatalog

_FEATURE_COLS = ("danceability", "energy", "valence", "acousticness", "instrumentalness")


def _cosine_sim(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def recommend_by_emotion(
    db: Session,
    emotion_vector: dict[str, float],
    top_k: int = 10,
) -> list[MusicCatalog]:
    query_vec = tuple(emotion_vector.get(f, 0.5) for f in _FEATURE_COLS)
    rows = db.query(MusicCatalog).all()

    scored = [
        (_cosine_sim(query_vec, tuple(getattr(r, f) for f in _FEATURE_COLS)), r)
        for r in rows
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_k]]
