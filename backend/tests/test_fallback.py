"""Fallback 경로 단위/통합 테스트 (Issue #43)"""

import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.routers.auth import get_current_user
from app.routers.recommend import router
from app.schemas.context import ContextResult
from app.services.context_analyzer import ContextAnalyzer, _rule_based_context, get_context_analyzer
from app.services.ml_client import VADResult, get_ml_client, vad_from_text
from app.services.reason_generator import ReasonGenerator, _rule_based_reason, get_reason_generator
from app.services.stt import get_stt_provider

SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class _MockUser:
    id = 1
    email = "test@example.com"


def _make_catalog_row(i: int) -> dict:
    return {
        "track_id": f"track_{i:03d}", "id": i + 1,
        "track_name": f"Track {i}", "artists": f"Artist {i}",
        "album_name": f"Album {i}", "track_genre": "pop",
        "popularity": 50, "duration_ms": 200_000, "preview_url": None,
        "danceability": 0.5, "energy": 0.5, "valence": 0.5,
        "acousticness": 0.2, "instrumentalness": 0.1,
        "speechiness": 0.05, "liveness": 0.1,
        "tempo": 120.0, "loudness": -8.0, "key": 0, "mode": 1, "time_signature": 4,
    }


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    from app.models.music_catalog import MusicCatalog
    db = TestingSessionLocal()
    for i in range(5):
        db.add(MusicCatalog(**_make_catalog_row(i)))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def _make_client(*, ml=None, stt=None, analyzer=None, reason_gen=None) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(router)

    def _db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    _default_stt = MagicMock()
    _default_stt.transcribe = AsyncMock(return_value="")
    _default_ml = MagicMock()
    _default_ml.predict = AsyncMock(return_value=VADResult(0.0, 0.0, 0.0))

    test_app.dependency_overrides[get_db] = _db
    test_app.dependency_overrides[get_current_user] = lambda: _MockUser()
    test_app.dependency_overrides[get_stt_provider] = lambda: (stt or _default_stt)
    test_app.dependency_overrides[get_ml_client] = lambda: (ml or _default_ml)
    test_app.dependency_overrides[get_context_analyzer] = lambda: analyzer
    test_app.dependency_overrides[get_reason_generator] = lambda: reason_gen

    return TestClient(test_app)


def _audio():
    return {"audio": ("test.wav", io.BytesIO(b"dummy"), "audio/wav")}


# ── vad_from_text 단위 테스트 ─────────────────────────────────────────────────

def test_vad_from_text_empty_returns_neutral():
    vad = vad_from_text("")
    assert vad.valence == 0.0 and vad.arousal == 0.0 and vad.dominance == 0.0


def test_vad_from_text_no_keyword_returns_neutral():
    vad = vad_from_text("오늘 날씨가 맑다")
    assert vad.valence == 0.0


def test_vad_from_text_happy_keyword_positive_valence():
    assert vad_from_text("기분이 너무 행복해").valence > 0.0


def test_vad_from_text_sad_keyword_negative_valence():
    assert vad_from_text("오늘 너무 슬프다").valence < 0.0


def test_vad_from_text_angry_keyword_high_arousal():
    assert vad_from_text("너무 화나고 짜증난다").arousal > 0.0


# ── ML fallback 통합 테스트 ───────────────────────────────────────────────────

def test_ml_fallback_flag_set_when_predict_fails():
    failing_ml = MagicMock()
    failing_ml.predict = AsyncMock(side_effect=Exception("connection refused"))
    with _make_client(ml=failing_ml) as c:
        res = c.post("/recommend", files=_audio())
    assert res.status_code == 200
    assert res.json()["fallback_flags"]["ml"] is True


def test_ml_no_fallback_when_predict_succeeds():
    ok_ml = MagicMock()
    ok_ml.predict = AsyncMock(return_value=VADResult(0.0, 0.0, 0.0))
    with _make_client(ml=ok_ml) as c:
        res = c.post("/recommend", files=_audio())
    assert res.json()["fallback_flags"]["ml"] is False


def test_ml_fallback_derives_valence_from_transcript():
    """ML 실패 + 행복 키워드 transcript → user_emotion.valence > 0.5"""
    failing_ml = MagicMock()
    failing_ml.predict = AsyncMock(side_effect=Exception("ML down"))
    stt = MagicMock()
    stt.transcribe = AsyncMock(return_value="오늘 너무 행복해")
    with _make_client(ml=failing_ml, stt=stt) as c:
        res = c.post("/recommend", files=_audio())
    assert res.status_code == 200
    assert res.json()["fallback_flags"]["ml"] is True
    assert res.json()["user_emotion"]["valence"] > 0.5


def test_ml_fallback_no_transcript_gives_neutral_emotion():
    failing_ml = MagicMock()
    failing_ml.predict = AsyncMock(side_effect=Exception("ML down"))
    with _make_client(ml=failing_ml) as c:
        res = c.post("/recommend", files=_audio())
    assert res.json()["fallback_flags"]["ml"] is True
    ue = res.json()["user_emotion"]
    assert ue["valence"] == pytest.approx(0.5, abs=0.01)


# ── STT 장애 내성 통합 테스트 (PR #169 리뷰 Medium #1) ───────────────────────
# STT 예외를 흡수해 transcript=None으로 응답하고 (요청 전체 500이 아님),
# context 분석은 transcript 부재로 자연스럽게 스킵된다.

def test_stt_failure_returns_200_with_null_transcript():
    failing_stt = MagicMock()
    failing_stt.transcribe = AsyncMock(side_effect=Exception("whisper crashed"))
    with _make_client(stt=failing_stt) as c:
        res = c.post("/recommend", files=_audio())
    assert res.status_code == 200
    assert res.json()["transcript"] is None


def test_stt_failure_skips_context_analysis():
    analyzer = MagicMock(spec=ContextAnalyzer)
    analyzer.analyze = AsyncMock(return_value=(ContextResult(), False))
    failing_stt = MagicMock()
    failing_stt.transcribe = AsyncMock(side_effect=Exception("whisper crashed"))
    with _make_client(stt=failing_stt, analyzer=analyzer) as c:
        res = c.post("/recommend", files=_audio())
    assert res.status_code == 200
    analyzer.analyze.assert_not_called()
    assert res.json()["context"] is None


# ── _rule_based_context 단위 테스트 ──────────────────────────────────────────

def test_rule_based_context_detects_time():
    assert _rule_based_context("아침에 커피 마시면서").time_of_day == "morning"


def test_rule_based_context_detects_location():
    assert _rule_based_context("카페에서 공부 중").location == "cafe"


def test_rule_based_context_detects_activity():
    assert _rule_based_context("헬스장에서 운동 중").activity == "exercising"


def test_rule_based_context_detects_emotion():
    result = _rule_based_context("너무 슬프고 우울해")
    assert result.emotions is not None and "sad" in result.emotions


def test_rule_based_context_no_keywords_all_none():
    result = _rule_based_context("오늘 날씨가 맑다")
    assert result.time_of_day is None
    assert result.location is None
    assert result.activity is None
    assert result.emotions is None


# ── Context fallback 통합 테스트 ──────────────────────────────────────────────

def test_context_fallback_flag_set():
    analyzer = MagicMock(spec=ContextAnalyzer)
    analyzer.analyze = AsyncMock(return_value=(ContextResult(), True))
    stt = MagicMock()
    stt.transcribe = AsyncMock(return_value="아침에 집에서 운동했어")
    with _make_client(analyzer=analyzer, stt=stt) as c:
        res = c.post("/recommend", files=_audio())
    assert res.json()["fallback_flags"]["context"] is True


def test_context_no_fallback_when_llm_succeeds():
    analyzer = MagicMock(spec=ContextAnalyzer)
    analyzer.analyze = AsyncMock(return_value=(ContextResult(), False))
    stt = MagicMock()
    stt.transcribe = AsyncMock(return_value="좋은 하루")
    with _make_client(analyzer=analyzer, stt=stt) as c:
        res = c.post("/recommend", files=_audio())
    assert res.json()["fallback_flags"]["context"] is False


# ── _rule_based_reason 단위 테스트 ────────────────────────────────────────────

def _make_track(**kwargs):
    from app.models.music_catalog import MusicCatalog
    defaults = {
        "track_id": "test_track",
        "track_name": "Test Track",
        "artists": "Test Artist",
        "album_name": "Test Album",
        "track_genre": "pop",
        "duration_ms": 200_000,
        "speechiness": 0.05,
        "liveness": 0.1,
        "tempo": 120.0,
        "loudness": -8.0,
        "key": 0,
        "mode": 1,
        "time_signature": 4,
        "danceability": 0.5,
        "energy": 0.5,
        "valence": 0.5,
        "acousticness": 0.2,
        "instrumentalness": 0.1,
    }
    defaults.update(kwargs)
    return MusicCatalog(**defaults)


def test_rule_based_reason_high_valence():
    assert "밝고 긍정적인 에너지" in _rule_based_reason(_make_track(valence=0.8))


def test_rule_based_reason_high_energy():
    assert "활기찬 비트" in _rule_based_reason(_make_track(energy=0.8))


def test_rule_based_reason_acoustic():
    assert "어쿠스틱한 감성" in _rule_based_reason(_make_track(acousticness=0.8))


def test_rule_based_reason_default_when_no_feature_matches():
    assert "현재 감정 상태에 어울리는 분위기" in _rule_based_reason(_make_track(acousticness=0.3))


# ── ReasonGenerator fallback 통합 테스트 ─────────────────────────────────────

def test_reason_fallback_flag_set():
    reason_gen = MagicMock(spec=ReasonGenerator)
    reason_gen.generate = AsyncMock(return_value=({"track_000": "rule reason"}, True))
    with _make_client(reason_gen=reason_gen) as c:
        res = c.post("/recommend", files=_audio())
    assert res.json()["fallback_flags"]["reason"] is True


def test_reason_no_fallback_when_llm_succeeds():
    reason_gen = MagicMock(spec=ReasonGenerator)
    reason_gen.generate = AsyncMock(return_value=({"track_000": "llm reason"}, False))
    with _make_client(reason_gen=reason_gen) as c:
        res = c.post("/recommend", files=_audio())
    assert res.json()["fallback_flags"]["reason"] is False
