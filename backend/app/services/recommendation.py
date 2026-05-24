"""RecommendationEngine — emotion vector → Spotify catalog cosine similarity matching (US-8)."""

from __future__ import annotations

import asyncio
import math

from app.services.spotify import _SpotifyAudioFeatures, _spotify_get, search_tracks

# ---------------------------------------------------------------------------
# Feature dimensions used for similarity vectors (order is fixed)
# ---------------------------------------------------------------------------
_FEATURE_KEYS: tuple[str, ...] = (
    "danceability",
    "energy",
    "valence",
    "acousticness",
    "instrumentalness",
)

# ---------------------------------------------------------------------------
# Emotion → normalized audio feature vector mapping
# ---------------------------------------------------------------------------
_EMOTION_VECTORS: dict[str, dict[str, float]] = {
    "happy": {
        "danceability": 0.75,
        "energy": 0.75,
        "valence": 0.85,
        "acousticness": 0.20,
        "instrumentalness": 0.10,
    },
    "sad": {
        "danceability": 0.30,
        "energy": 0.25,
        "valence": 0.15,
        "acousticness": 0.65,
        "instrumentalness": 0.30,
    },
    "angry": {
        "danceability": 0.55,
        "energy": 0.90,
        "valence": 0.25,
        "acousticness": 0.10,
        "instrumentalness": 0.15,
    },
    "relaxed": {
        "danceability": 0.45,
        "energy": 0.25,
        "valence": 0.60,
        "acousticness": 0.75,
        "instrumentalness": 0.50,
    },
    "anxious": {
        "danceability": 0.50,
        "energy": 0.65,
        "valence": 0.35,
        "acousticness": 0.30,
        "instrumentalness": 0.25,
    },
    "neutral": {
        "danceability": 0.50,
        "energy": 0.50,
        "valence": 0.50,
        "acousticness": 0.50,
        "instrumentalness": 0.25,
    },
}

# Seed Spotify search queries per emotion for catalog building
_EMOTION_SEED_QUERIES: dict[str, list[str]] = {
    "happy":   ["happy upbeat pop", "feel good dance hits"],
    "sad":     ["sad acoustic indie", "melancholy piano"],
    "angry":   ["intense rock metal", "aggressive electronic"],
    "relaxed": ["chill ambient lo-fi", "peaceful instrumental"],
    "anxious": ["tense cinematic score", "dark electronic"],
    "neutral": ["popular top tracks", "indie hits 2024"],
}

SUPPORTED_EMOTIONS = list(_EMOTION_VECTORS.keys())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_feature_vector(features: dict[str, float]) -> list[float]:
    return [features.get(k, 0.0) for k in _FEATURE_KEYS]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _get_batch_audio_features(track_ids: list[str]) -> dict[str, dict[str, float]]:
    """Fetch audio features for up to 100 tracks in a single Spotify API call."""
    if not track_ids:
        return {}
    raw = await _spotify_get("/audio-features", params={"ids": ",".join(track_ids[:100])})
    result: dict[str, dict[str, float]] = {}
    for item in raw.get("audio_features") or []:
        if item is None:
            continue
        try:
            features = _SpotifyAudioFeatures.model_validate(item)
            result[item["id"]] = {
                "danceability": features.danceability,
                "energy": features.energy,
                "valence": features.valence,
                "acousticness": features.acousticness,
                "instrumentalness": features.instrumentalness,
            }
        except Exception:
            continue
    return result


async def _build_catalog(emotion: str, per_query_limit: int = 20) -> list[dict]:
    """Search Spotify with emotion-specific seed queries to build a candidate catalog."""
    queries = _EMOTION_SEED_QUERIES.get(emotion.lower(), _EMOTION_SEED_QUERIES["neutral"])
    results = await asyncio.gather(
        *[search_tracks(q, limit=per_query_limit) for q in queries],
        return_exceptions=True,
    )
    seen: set[str] = set()
    tracks: list[dict] = []
    for result in results:
        if isinstance(result, Exception):
            continue
        for t in result.get("tracks", []):
            if t["track_id"] not in seen:
                seen.add(t["track_id"])
                tracks.append(t)
    return tracks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def emotion_to_vector(emotion: str) -> list[float]:
    """Map an emotion label to a normalized audio feature vector."""
    feature_map = _EMOTION_VECTORS.get(emotion.lower(), _EMOTION_VECTORS["neutral"])
    return [feature_map[k] for k in _FEATURE_KEYS]


async def recommend_by_emotion(emotion: str, top_k: int = 10) -> list[dict]:
    """Return top_k Spotify tracks ranked by cosine similarity to the emotion vector.

    Raises SpotifyCredentialsError or RateLimitError from the spotify service on failure.
    """
    emotion_vec = emotion_to_vector(emotion)
    catalog = await _build_catalog(emotion)
    if not catalog:
        return []

    features_map = await _get_batch_audio_features([t["track_id"] for t in catalog])

    scored: list[tuple[float, dict]] = []
    for track in catalog:
        tid = track["track_id"]
        if tid not in features_map:
            continue
        score = _cosine_similarity(emotion_vec, _to_feature_vector(features_map[tid]))
        scored.append((score, track))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:top_k]]
