"""
ContextAnalyzer 테스트 — 실제 Gemini API 호출 (GEMINI_API_KEY 필수)

ContextResult 검증 테스트는 API 키 없이도 동작하나,
analyzer를 사용하는 모든 테스트는 실제 Gemini API를 호출합니다.
"""

import io
import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.models.music_catalog import MusicCatalog
from app.routers.recommend import router
from app.services.context_analyzer import ContextAnalyzer, ContextResult, get_context_analyzer

# ---------------------------------------------------------------------------
# DB fixture
# ---------------------------------------------------------------------------

SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _catalog_row(i: int) -> dict:
    return {
        "track_id": f"t{i:03d}",
        "track_name": f"Track {i}",
        "artists": f"Artist {i}",
        "album_name": f"Album {i}",
        "track_genre": "pop",
        "popularity": 50,
        "duration_ms": 200_000,
        "preview_url": None,
        "danceability": 0.5,
        "energy": 0.5,
        "valence": 0.5,
        "acousticness": 0.1,
        "instrumentalness": 0.0,
        "speechiness": 0.05,
        "liveness": 0.1,
        "tempo": 120.0,
        "loudness": -8.0,
        "key": 0,
        "mode": 1,
        "time_signature": 4,
    }


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    for i in range(10):
        db.add(MusicCatalog(**_catalog_row(i)))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Analyzer fixture — GEMINI_API_KEY 없으면 skip
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def analyzer():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY 미설정 — 실제 API 테스트 skip")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
    return ContextAnalyzer(api_key=api_key, model_name=model)


# ---------------------------------------------------------------------------
# ContextResult 검증 — API 키 불필요
# ---------------------------------------------------------------------------

def test_context_result_accepts_valid_fields():
    r = ContextResult(
        time_of_day="evening",
        location="home",
        activity="relaxing",
        emotions={"calm": 0.7, "melancholic": 0.3},
    )
    assert r.time_of_day == "evening"
    assert r.emotions == {"calm": 0.7, "melancholic": 0.3}


def test_context_result_rejects_unknown_time_of_day():
    assert ContextResult(time_of_day="noon").time_of_day is None


def test_context_result_rejects_unknown_location():
    assert ContextResult(location="space").location is None


def test_context_result_rejects_unknown_activity():
    assert ContextResult(activity="skydiving").activity is None


def test_context_result_filters_invalid_emotion_labels():
    r = ContextResult(emotions={"happy": 0.8, "confused": 0.2})
    assert r.emotions == {"happy": 0.8}


def test_context_result_returns_none_emotions_when_all_invalid():
    assert ContextResult(emotions={"confused": 1.0}).emotions is None


def test_context_result_tolerates_non_numeric_emotion_score():
    r = ContextResult(emotions={"happy": "high", "calm": 0.6})
    assert r.emotions == {"calm": 0.6}


def test_get_context_analyzer_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import app.services.context_analyzer as mod
    mod._analyzer = None
    assert get_context_analyzer() is None


# ---------------------------------------------------------------------------
# ContextAnalyzer — 실제 Gemini API 호출
# ---------------------------------------------------------------------------

async def test_analyze_empty_text_returns_empty(analyzer):
    result = await analyzer.analyze("")
    assert result == ContextResult()


async def test_analyze_commuting(analyzer):
    text = "지하철 타고 출근 중이야, 사람 많고 피곤해"
    result = await analyzer.analyze(text)
    print(f"\n[입력] {text}")
    print(f"[결과] {result}")
    assert result.location == "commute"
    assert result.activity == "commuting"


async def test_analyze_home_evening(analyzer):
    text = "집에서 저녁에 음악 들으며 쉬고 있어"
    result = await analyzer.analyze(text)
    print(f"\n[입력] {text}")
    print(f"[결과] {result}")
    assert result.time_of_day == "evening"
    assert result.location == "home"
    assert result.activity == "relaxing"


async def test_analyze_gym_workout(analyzer):
    text = "헬스장에서 운동 중이야, 기분 너무 좋다!"
    result = await analyzer.analyze(text)
    print(f"\n[입력] {text}")
    print(f"[결과] {result}")
    assert result.location == "gym"
    assert result.activity == "exercising"


async def test_analyze_study_cafe(analyzer):
    text = "카페에서 시험 공부 중, 집중이 안 된다"
    result = await analyzer.analyze(text)
    print(f"\n[입력] {text}")
    print(f"[결과] {result}")
    assert result.location == "cafe"
    assert result.activity == "studying"


async def test_analyze_emotions_are_valid_schema(analyzer):
    text = "요즘 너무 불안하고 우울해, 아무것도 하기 싫어"
    result = await analyzer.analyze(text)
    print(f"\n[입력] {text}")
    print(f"[결과] emotions={result.emotions}")
    valid_labels = {"happy", "sad", "angry", "anxious", "calm", "energetic", "melancholic"}
    if result.emotions:
        for label, score in result.emotions.items():
            assert label in valid_labels, f"알 수 없는 감정 레이블: {label}"
            assert 0.0 <= score <= 1.0, f"score 범위 초과: {score}"


async def test_analyze_returns_valid_context_result_type(analyzer):
    result = await analyzer.analyze("오늘 재택근무 중, 점심 먹고 졸리다")
    print(f"\n[결과] {result}")
    assert isinstance(result, ContextResult)
    if result.time_of_day is not None:
        assert result.time_of_day in {"morning", "afternoon", "evening", "night"}
    if result.location is not None:
        assert result.location in {"home", "commute", "gym", "office", "outdoor", "cafe"}
    if result.activity is not None:
        assert result.activity in {"working", "exercising", "relaxing", "studying", "commuting", "socializing"}


# ---------------------------------------------------------------------------
# /recommend 엔드포인트 — 실제 API 연동
# ---------------------------------------------------------------------------

def _make_client(analyzer_instance) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(router)

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_context_analyzer] = lambda: analyzer_instance
    return TestClient(test_app)


def test_recommend_returns_context_with_transcript(analyzer):
    client = _make_client(analyzer)
    res = client.post(
        "/recommend",
        files={"audio": ("t.wav", io.BytesIO(b"x"), "audio/wav")},
        data={"transcript": "집에서 저녁에 음악 들으며 쉬고 있어"},
    )
    assert res.status_code == 200
    ctx = res.json().get("context")
    assert ctx is not None
    assert ctx.get("time_of_day") is not None or ctx.get("location") is not None


def test_recommend_context_null_without_transcript():
    client = _make_client(None)
    res = client.post("/recommend", files={"audio": ("t.wav", io.BytesIO(b"x"), "audio/wav")})
    assert res.status_code == 200
    assert res.json().get("context") is None
