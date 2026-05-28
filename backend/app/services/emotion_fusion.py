from app.schemas.context import ContextResult

# ContextResult.emotions의 감정 레이블 → Spotify 특징 조정 (가중치 1.0 기준)
_EMOTION_DELTAS: dict[str, dict[str, float]] = {
    "happy":       {"valence": +0.2, "energy": +0.1, "danceability": +0.1, "acousticness": -0.1},
    "sad":         {"valence": -0.2, "energy": -0.2, "danceability": -0.1, "acousticness": +0.2},
    "angry":       {"energy": +0.2, "danceability": +0.1, "acousticness": -0.1},
    "anxious":     {"valence": -0.1, "energy": +0.1, "acousticness": -0.1},
    "calm":        {"energy": -0.2, "acousticness": +0.2, "danceability": -0.1},
    "energetic":   {"energy": +0.2, "danceability": +0.2, "acousticness": -0.1},
    "melancholic": {"valence": -0.2, "energy": -0.1, "acousticness": +0.2, "instrumentalness": +0.1},
}

_TIME_BIAS: dict[str, dict[str, float]] = {
    "morning":   {"valence": +0.05, "energy": +0.05},
    "afternoon": {"energy": +0.05},
    "evening":   {"energy": -0.05, "acousticness": +0.05},
    "night":     {"energy": -0.10, "acousticness": +0.10, "instrumentalness": +0.05},
}

_LOCATION_BIAS: dict[str, dict[str, float]] = {
    "home":     {"acousticness": +0.10, "energy": -0.05},
    "commute":  {"energy": +0.10},
    "gym":      {"energy": +0.15, "danceability": +0.10, "acousticness": -0.10},
    "office":   {"instrumentalness": +0.10, "energy": -0.05},
    "outdoor":  {"energy": +0.10, "valence": +0.05},
    "cafe":     {"acousticness": +0.10, "energy": -0.05},
}

_ACTIVITY_BIAS: dict[str, dict[str, float]] = {
    "working":    {"instrumentalness": +0.10, "energy": -0.05},
    "exercising": {"energy": +0.20, "danceability": +0.15, "acousticness": -0.10},
    "relaxing":   {"energy": -0.15, "acousticness": +0.15},
    "studying":   {"instrumentalness": +0.15, "energy": -0.10, "acousticness": +0.10},
    "commuting":  {"energy": +0.10},
    "socializing": {"valence": +0.10, "danceability": +0.15},
}

# context 감정이 특징에 미치는 최대 영향 비율 (0.4 = 최대 ±0.4 이동)
_CONTEXT_EMOTION_WEIGHT = 0.4


def fuse(
    vad_valence: float,
    vad_arousal: float,
    vad_dominance: float,  # noqa: ARG001 — reserved for future weighting
    context: ContextResult | None = None,
) -> dict[str, float]:
    """ML VAD 벡터와 맥락 정보를 Spotify 오디오 특징 공간으로 융합한다.

    Args:
        vad_valence: ML 감정 벡터의 valence [-1, 1]
        vad_arousal: ML 감정 벡터의 arousal [-1, 1]
        vad_dominance: ML 감정 벡터의 dominance [-1, 1]
        context: ContextAnalyzer 결과 (없으면 VAD 기반 기본값만 사용)

    Returns:
        RecommendationEngine이 요구하는 Spotify 특징 dict (모든 값 [0, 1])
    """
    # Step 1: VAD[-1, 1] → [0, 1] 정규화 후 Spotify 특징 초기값 설정
    vn = (vad_valence + 1) / 2
    an = (vad_arousal + 1) / 2

    features: dict[str, float] = {
        "valence":         vn,
        "energy":          an,
        "danceability":    0.6 * an + 0.4 * vn,  # arousal 우세 + valence 보조
        "acousticness":    1.0 - an,              # 낮은 arousal → acoustic
        "instrumentalness": 0.5,                  # 기본 중립
    }

    if context is not None:
        # Step 2: 맥락 감정 가중 조정
        if context.emotions:
            total = sum(context.emotions.values())
            if total > 0:
                for emotion, score in context.emotions.items():
                    w = (score / total) * _CONTEXT_EMOTION_WEIGHT
                    for feat, delta in _EMOTION_DELTAS.get(emotion, {}).items():
                        features[feat] += w * delta

        # Step 3: 시간대/장소/활동 바이어스 가산
        for bias_table, key in (
            (_TIME_BIAS, context.time_of_day),
            (_LOCATION_BIAS, context.location),
            (_ACTIVITY_BIAS, context.activity),
        ):
            if key and key in bias_table:
                for feat, delta in bias_table[key].items():
                    features[feat] += delta

    # Step 4: [0, 1] 클램핑
    return {k: max(0.0, min(1.0, val)) for k, val in features.items()}
