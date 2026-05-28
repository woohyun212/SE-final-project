import io
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
import app.models  # noqa: F401
from app.models.music_catalog import MusicCatalog
from app.routers.recommend import router
from app.services.context_analyzer import ContextAnalyzer, ContextResult, get_context_analyzer

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
# ContextResult validation
# ---------------------------------------------------------------------------

def test_context_result_accepts_valid_fields():
    print("\n[입력] time_of_day='evening', location='home', activity='relaxing', emotions={'calm': 0.7, 'melancholic': 0.3}")
    r = ContextResult(
        time_of_day="evening",
        location="home",
        activity="relaxing",
        emotions={"calm": 0.7, "melancholic": 0.3},
    )
    print(f"[결과] time_of_day={r.time_of_day!r}, location={r.location!r}, emotions={r.emotions}")
    assert r.time_of_day == "evening"
    assert r.emotions == {"calm": 0.7, "melancholic": 0.3}


def test_context_result_rejects_unknown_time_of_day():
    print("\n[입력] time_of_day='noon'  (허용값: morning/afternoon/evening/night)")
    r = ContextResult(time_of_day="noon")
    print(f"[결과] time_of_day={r.time_of_day!r}  → 유효하지 않으므로 None으로 변환")
    assert r.time_of_day is None


def test_context_result_rejects_unknown_location():
    print("\n[입력] location='space'  (허용값: home/commute/gym/office/outdoor/cafe)")
    r = ContextResult(location="space")
    print(f"[결과] location={r.location!r}  → 유효하지 않으므로 None으로 변환")
    assert r.location is None


def test_context_result_rejects_unknown_activity():
    print("\n[입력] activity='skydiving'  (허용값: working/exercising/relaxing/studying/commuting/socializing)")
    r = ContextResult(activity="skydiving")
    print(f"[결과] activity={r.activity!r}  → 유효하지 않으므로 None으로 변환")
    assert r.activity is None


def test_context_result_filters_invalid_emotion_labels():
    print("\n[입력] emotions={'happy': 0.8, 'confused': 0.2}  ('confused'는 허용 레이블 아님)")
    r = ContextResult(emotions={"happy": 0.8, "confused": 0.2})
    print(f"[결과] emotions={r.emotions}  → 'confused' 제거, 'happy'만 보존")
    assert "confused" not in (r.emotions or {})
    assert r.emotions == {"happy": 0.8}


def test_context_result_returns_none_emotions_when_all_invalid():
    print("\n[입력] emotions={'confused': 1.0}  (유효한 레이블 전혀 없음)")
    r = ContextResult(emotions={"confused": 1.0})
    print(f"[결과] emotions={r.emotions}  → 유효한 항목이 없으므로 None 반환")
    assert r.emotions is None


def test_context_result_tolerates_non_numeric_emotion_score():
    print("\n[입력] emotions={'happy': 'high', 'calm': 0.6}  (LLM이 숫자 대신 문자열 반환하는 경우)")
    r = ContextResult(
        time_of_day="evening",
        location="home",
        emotions={"happy": "high", "calm": 0.6},
    )
    print(f"[결과] time_of_day={r.time_of_day!r}, location={r.location!r}, emotions={r.emotions}")
    print("  → 'happy': 'high'는 float 변환 실패로 제거, 나머지 필드는 정상 보존")
    assert r.time_of_day == "evening"
    assert r.location == "home"
    assert r.emotions == {"calm": 0.6}


# ---------------------------------------------------------------------------
# ContextAnalyzer.analyze — unit (Gemini mocked)
# ---------------------------------------------------------------------------

def _make_analyzer() -> ContextAnalyzer:
    with patch("google.genai.Client"):
        return ContextAnalyzer(api_key="fake-key")


async def test_analyze_returns_parsed_result():
    analyzer = _make_analyzer()
    input_text = "I'm rushing to work on the subway, running a bit late"
    payload = json.dumps({
        "time_of_day": "morning",
        "location": "commute",
        "activity": "commuting",
        "emotions": {"anxious": 0.6, "energetic": 0.4},
    })
    print(f"\n[입력 텍스트] {input_text!r}")
    print(f"[LLM 응답 mock] {payload}")

    mock_response = MagicMock()
    mock_response.text = payload
    analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await analyzer.analyze(input_text)
    print(f"[파싱 결과] time_of_day={result.time_of_day!r}, location={result.location!r}, "
          f"activity={result.activity!r}, emotions={result.emotions}")
    assert result.time_of_day == "morning"
    assert result.location == "commute"
    assert result.activity == "commuting"
    assert result.emotions is not None
    assert "anxious" in result.emotions


async def test_analyze_strips_markdown_fences():
    analyzer = _make_analyzer()
    input_text = "Can't sleep again"
    raw_payload = '```json\n{"time_of_day": "night", "location": null, "activity": null, "emotions": null}\n```'
    print(f"\n[입력 텍스트] {input_text!r}")
    print(f"[LLM 응답 mock - markdown fence 포함]\n{raw_payload}")

    mock_response = MagicMock()
    mock_response.text = raw_payload
    analyzer._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    result = await analyzer.analyze(input_text)
    print(f"[파싱 결과] time_of_day={result.time_of_day!r}  → fence 제거 후 정상 파싱")
    assert result.time_of_day == "night"


async def test_analyze_returns_empty_result_on_llm_error():
    analyzer = _make_analyzer()
    input_text = "some text"
    print(f"\n[입력 텍스트] {input_text!r}")
    print("[LLM 응답 mock] Exception('network error') 발생 시뮬레이션")

    analyzer._client.aio.models.generate_content = AsyncMock(side_effect=Exception("network error"))

    result = await analyzer.analyze(input_text)
    print(f"[결과] {result}  → 오류 발생 시 빈 ContextResult 반환 (서비스 중단 없음)")
    assert result == ContextResult()


async def test_analyze_empty_text_skips_llm():
    analyzer = _make_analyzer()
    print("\n[입력 텍스트] ''  (빈 문자열)")
    print("[기대 동작] LLM 호출 없이 빈 ContextResult 즉시 반환")

    analyzer._client.aio.models.generate_content = AsyncMock()

    result = await analyzer.analyze("")
    called = analyzer._client.aio.models.generate_content.called
    print(f"[결과] LLM 호출 여부={called}, result={result}")
    analyzer._client.aio.models.generate_content.assert_not_called()
    assert result == ContextResult()


# ---------------------------------------------------------------------------
# get_context_analyzer — returns None when key absent
# ---------------------------------------------------------------------------

def test_get_context_analyzer_returns_none_without_key(monkeypatch):
    print("\n[조건] GEMINI_API_KEY 환경 변수 없음")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import app.services.context_analyzer as mod
    mod._analyzer = None
    result = get_context_analyzer()
    print(f"[결과] get_context_analyzer() = {result}  → API 키 없으면 None 반환 (NFR2.3 fallback)")
    assert result is None


# ---------------------------------------------------------------------------
# /recommend endpoint — context integration
# ---------------------------------------------------------------------------

def _make_client(analyzer_override) -> TestClient:
    test_app = FastAPI()
    test_app.include_router(router)

    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_db
    test_app.dependency_overrides[get_context_analyzer] = lambda: analyzer_override

    return TestClient(test_app)


def test_recommend_context_included_when_transcript_provided():
    print("\n[조건] transcript='Chilling at home in the evening' + analyzer 활성화")
    analyzer = _make_analyzer()

    async def fake_analyze(text: str) -> ContextResult:
        return ContextResult(time_of_day="evening", location="home", activity="relaxing")

    analyzer.analyze = fake_analyze

    client = _make_client(analyzer)
    res = client.post(
        "/recommend",
        files={"audio": ("t.wav", io.BytesIO(b"x"), "audio/wav")},
        data={"transcript": "Chilling at home in the evening"},
    )
    ctx = res.json().get("context")
    print(f"[응답] status={res.status_code}, context={ctx}")
    assert res.status_code == 200
    assert ctx is not None
    assert ctx["time_of_day"] == "evening"
    assert ctx["location"] == "home"


def test_recommend_context_null_without_transcript():
    print("\n[조건] transcript 없음 (오디오만 전송)")
    client = _make_client(analyzer_override=None)
    res = client.post("/recommend", files={"audio": ("t.wav", io.BytesIO(b"x"), "audio/wav")})
    ctx = res.json().get("context")
    print(f"[응답] status={res.status_code}, context={ctx}  → transcript 없으면 context=null")
    assert res.status_code == 200
    assert ctx is None


def test_recommend_context_null_when_analyzer_disabled():
    print("\n[조건] transcript 있음 + analyzer=None (GEMINI_API_KEY 미설정 상태)")
    client = _make_client(analyzer_override=None)
    res = client.post(
        "/recommend",
        files={"audio": ("t.wav", io.BytesIO(b"x"), "audio/wav")},
        data={"transcript": "some text"},
    )
    ctx = res.json().get("context")
    print(f"[응답] status={res.status_code}, context={ctx}  → analyzer 비활성화 시 context=null")
    assert res.status_code == 200
    assert ctx is None


# ---------------------------------------------------------------------------
# 실제 Gemini API 통합 테스트 — GEMINI_API_KEY 없으면 자동 skip
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY 미설정 — 실제 API 테스트 skip",
)
async def test_analyze_real_api():
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
    print(f"\n[실제 API 호출] model={model_name}")
    print("[입력 텍스트] '집에서 저녁에 음악 들으며 쉬고 있어'")

    analyzer = ContextAnalyzer(api_key=api_key, model_name=model_name)
    result = await analyzer.analyze("집에서 저녁에 음악 들으며 쉬고 있어")

    print(f"[API 응답] time_of_day={result.time_of_day!r}, location={result.location!r}, "
          f"activity={result.activity!r}, emotions={result.emotions}")
    assert isinstance(result, ContextResult)
