import pytest

from app.schemas.context import ContextResult
from app.services.emotion_fusion import fuse

_FEATURES = ("valence", "energy", "danceability", "acousticness", "instrumentalness")


def _in_range(vec: dict[str, float]) -> bool:
    return all(0.0 <= vec[f] <= 1.0 for f in _FEATURES)


def _has_all_keys(vec: dict[str, float]) -> bool:
    return set(vec.keys()) == set(_FEATURES)


# ── 기본 VAD 매핑 ─────────────────────────────────────────────────────────────

def test_output_has_all_feature_keys():
    assert _has_all_keys(fuse(0.0, 0.0, 0.0))


def test_vad_neutral_maps_to_midpoint():
    """VAD (0, 0, 0) → valence·energy 모두 0.5"""
    vec = fuse(0.0, 0.0, 0.0)
    assert abs(vec["valence"] - 0.5) < 1e-6
    assert abs(vec["energy"] - 0.5) < 1e-6


def test_high_valence_arousal_positive_features():
    """높은 valence, arousal → 높은 energy·valence·danceability"""
    vec = fuse(0.8, 0.8, 0.5)
    assert vec["valence"] > 0.7
    assert vec["energy"] > 0.7
    assert vec["danceability"] > 0.6
    assert _in_range(vec)


def test_low_valence_low_arousal_sad():
    """낮은 valence, arousal (슬픔 계열) → 낮은 valence·energy, 높은 acousticness"""
    vec = fuse(-0.7, -0.4, -0.5)
    assert vec["valence"] < 0.3
    assert vec["energy"] < 0.4
    assert vec["acousticness"] > 0.5
    assert _in_range(vec)


def test_acousticness_inverse_of_energy():
    """arousal 상승 → energy 상승, acousticness 하락 (반비례 관계 유지)"""
    low = fuse(0.0, -0.5, 0.0)
    high = fuse(0.0, 0.5, 0.0)
    assert high["energy"] > low["energy"]
    assert high["acousticness"] < low["acousticness"]


# ── 경계값 및 범위 보장 ────────────────────────────────────────────────────────

def test_output_clamped_extreme_max():
    assert _in_range(fuse(1.0, 1.0, 1.0))


def test_output_clamped_extreme_min():
    assert _in_range(fuse(-1.0, -1.0, -1.0))


def test_output_clamped_with_context():
    """강한 바이어스가 겹쳐도 [0, 1] 유지"""
    ctx = ContextResult(
        location="gym",
        activity="exercising",
        time_of_day="afternoon",
        emotions={"energetic": 1.0},
    )
    assert _in_range(fuse(1.0, 1.0, 1.0, context=ctx))
    assert _in_range(fuse(-1.0, -1.0, -1.0, context=ctx))


# ── context=None / 빈 context ──────────────────────────────────────────────────

def test_no_context_returns_base_features():
    """context=None 이면 VAD 기반 기본값만 반환"""
    vec = fuse(0.5, 0.3, 0.0, context=None)
    assert _has_all_keys(vec)
    assert _in_range(vec)


def test_empty_context_same_as_no_context():
    """빈 ContextResult(모든 필드 None)는 context=None과 동일한 결과"""
    vad = (0.3, -0.2, 0.1)
    vec_none = fuse(*vad, context=None)
    vec_empty = fuse(*vad, context=ContextResult())
    assert all(abs(vec_none[f] - vec_empty[f]) < 1e-9 for f in _FEATURES)


# ── context 감정 조정 ──────────────────────────────────────────────────────────

def test_happy_emotion_raises_valence():
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ContextResult(emotions={"happy": 1.0}))
    assert vec["valence"] > baseline["valence"]
    assert _in_range(vec)


def test_sad_emotion_lowers_valence_and_energy():
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ContextResult(emotions={"sad": 1.0}))
    assert vec["valence"] < baseline["valence"]
    assert vec["energy"] < baseline["energy"]
    assert _in_range(vec)


def test_calm_emotion_raises_acousticness():
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ContextResult(emotions={"calm": 1.0}))
    assert vec["acousticness"] > baseline["acousticness"]
    assert _in_range(vec)


def test_energetic_emotion_raises_energy_and_danceability():
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ContextResult(emotions={"energetic": 1.0}))
    assert vec["energy"] > baseline["energy"]
    assert vec["danceability"] > baseline["danceability"]
    assert _in_range(vec)


def test_multiple_emotions_weighted():
    """여러 감정이 있을 때 비율대로 가중 적용"""
    # happy(0.5) + sad(0.5) → 서로 상쇄, 기준값에 근접
    ctx = ContextResult(emotions={"happy": 0.5, "sad": 0.5})
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ctx)
    # valence 변화가 단독 happy / sad보다 작아야 함
    happy_vec = fuse(0.0, 0.0, 0.0, context=ContextResult(emotions={"happy": 1.0}))
    assert abs(vec["valence"] - baseline["valence"]) < abs(happy_vec["valence"] - baseline["valence"])
    assert _in_range(vec)


# ── context 메타데이터 바이어스 ────────────────────────────────────────────────

def test_gym_location_raises_energy():
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ContextResult(location="gym"))
    assert vec["energy"] > baseline["energy"]
    assert vec["danceability"] > baseline["danceability"]
    assert _in_range(vec)


def test_studying_activity_raises_instrumentalness():
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ContextResult(activity="studying"))
    assert vec["instrumentalness"] > baseline["instrumentalness"]
    assert _in_range(vec)


def test_night_time_lowers_energy():
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ContextResult(time_of_day="night"))
    assert vec["energy"] < baseline["energy"]
    assert _in_range(vec)


def test_relaxing_activity_lowers_energy_raises_acousticness():
    baseline = fuse(0.0, 0.0, 0.0)
    vec = fuse(0.0, 0.0, 0.0, context=ContextResult(activity="relaxing"))
    assert vec["energy"] < baseline["energy"]
    assert vec["acousticness"] > baseline["acousticness"]
    assert _in_range(vec)


# ── 복합 입력 ──────────────────────────────────────────────────────────────────

def test_combined_context_all_fields():
    """모든 context 필드가 채워진 케이스에서도 범위·키 보장"""
    ctx = ContextResult(
        time_of_day="night",
        location="home",
        activity="relaxing",
        emotions={"calm": 0.8, "melancholic": 0.5},
    )
    vec = fuse(-0.3, -0.5, 0.0, context=ctx)
    assert _has_all_keys(vec)
    assert _in_range(vec)
    # 모두 조용한/편안한 컨텍스트 → acousticness 높고 energy 낮아야 함
    baseline = fuse(-0.3, -0.5, 0.0)
    assert vec["acousticness"] > baseline["acousticness"]
    assert vec["energy"] < baseline["energy"]


def test_happy_gym_socializing():
    """긍정적 감정 + 활동적 장소/활동 → 높은 energy·danceability·valence"""
    ctx = ContextResult(
        time_of_day="afternoon",
        location="gym",
        activity="exercising",
        emotions={"happy": 0.9, "energetic": 0.8},
    )
    vec = fuse(0.5, 0.5, 0.0, context=ctx)
    baseline = fuse(0.5, 0.5, 0.0)
    assert vec["energy"] > baseline["energy"]
    assert vec["danceability"] > baseline["danceability"]
    assert _in_range(vec)
