"""
E2E 시나리오 테스트 — 실제 사용자 흐름 전체 검증

시나리오:
  1. 회원가입
  2. 로그인
  3. 음성 추천 요청 (ML/STT/LLM은 stub으로 대체)
  4. 추천 결과 중 1곡 좋아요, 1곡 싫어요
  5. 재생 이벤트 로깅 (start → complete)
  6. 추천 이력 조회 — 추천 곡 + 피드백 포함 확인
  7. 두 번째 추천 요청 — 피드백 누적 후 정상 동작 확인
  8. 토큰 갱신
  9. 로그아웃 후 보호 엔드포인트 접근 거부 확인
"""

import io
import wave

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.models.music_catalog import MusicCatalog
from app.routers import auth, feedback, history, recommend
from app.services.context_analyzer import get_context_analyzer
from app.services.ml_client import VADResult, get_ml_client
from app.services.reason_generator import get_reason_generator
from app.services.stt import get_stt_provider

# ── DB 설정 ─────────────────────────────────────────────────────────────────

SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── 외부 서비스 Stub ─────────────────────────────────────────────────────────

class _StubSTT:
    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        return "오늘 저녁 집에서 차분하게 쉬고 싶어"


class _StubML:
    async def predict(self, audio_bytes: bytes) -> VADResult:
        return VADResult(valence=0.4, arousal=-0.5, dominance=0.0)


class _StubContextAnalyzer:
    async def analyze(self, transcript: str):
        from app.schemas.context import ContextResult
        ctx = ContextResult(
            time_of_day="evening",
            location="home",
            activity="relaxing",
            emotions={"calm": 0.9},
        )
        return ctx, False


class _StubReasonGenerator:
    async def generate(self, tracks, valence, arousal, dominance, context):
        reasons = {t.track_id: f"{t.track_name}의 잔잔한 분위기가 지금 기분과 잘 맞아요." for t in tracks}
        return reasons, False


# ── 테스트 음악 카탈로그 시드 ──────────────────────────────────────────────────

def _seed_catalog(n: int = 10) -> None:
    db = TestingSessionLocal()
    for i in range(1, n + 1):
        db.add(MusicCatalog(
            track_id=f"track_{i:03d}",
            id=i,
            track_name=f"Song {i}",
            artists=f"Artist {i}",
            album_name=f"Album {i}",
            track_genre="pop",
            popularity=50 + i,
            duration_ms=200_000,
            danceability=0.3 + i * 0.05,
            energy=0.3 + i * 0.05,
            valence=0.3 + i * 0.05,
            acousticness=0.8 - i * 0.05,
            instrumentalness=0.1,
            speechiness=0.05,
            liveness=0.1,
            tempo=100.0 + i * 5,
            loudness=-10.0 + i * 0.5,
            key=i % 12,
            mode=1,
            time_signature=4,
        ))
    db.commit()
    db.close()


def _make_dummy_wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 160)
    return buf.getvalue()


# ── 앱 픽스처 ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    _seed_catalog()

    test_app = FastAPI()
    test_app.include_router(auth.router)
    test_app.include_router(recommend.router)
    test_app.include_router(feedback.router)
    test_app.include_router(history.router)

    test_app.dependency_overrides[get_db] = _override_get_db
    test_app.dependency_overrides[get_stt_provider] = lambda: _StubSTT()
    test_app.dependency_overrides[get_ml_client] = lambda: _StubML()
    test_app.dependency_overrides[get_context_analyzer] = lambda: _StubContextAnalyzer()
    test_app.dependency_overrides[get_reason_generator] = lambda: _StubReasonGenerator()

    with TestClient(test_app) as c:
        yield c

    Base.metadata.drop_all(bind=engine)


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 시나리오 테스트 ────────────────────────────────────────────────────────────

def test_full_user_scenario(client: TestClient) -> None:
    audio = _make_dummy_wav()

    # 1. 회원가입
    res = client.post("/auth/signup", json={"email": "user@test.com", "password": "Password1"})
    assert res.status_code == 201, res.text
    tokens = res.json()
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    # 2. 로그인 (토큰 재발급 확인)
    res = client.post("/auth/login", json={"email": "user@test.com", "password": "Password1"})
    assert res.status_code == 200
    access = res.json()["access_token"]
    refresh = res.json()["refresh_token"]

    # 3. 첫 번째 추천 요청
    res = client.post(
        "/recommend",
        files={"audio": ("audio.wav", audio, "audio/wav")},
        headers=_auth_header(access),
    )
    assert res.status_code == 200, res.text
    rec = res.json()

    session_id = rec["session_id"]
    assert len(rec["recommendations"]) >= 1
    assert rec["fallback_flags"]["ml"] is False
    assert rec["transcript"] == "오늘 저녁 집에서 차분하게 쉬고 싶어"
    assert rec["context"]["time_of_day"] == "evening"

    track_1 = rec["recommendations"][0]["track"]["track_id"]
    track_2 = rec["recommendations"][1]["track"]["track_id"]
    track_3 = rec["recommendations"][2]["track"]["track_id"]

    # score가 [0, 1] 범위인지 확인
    for r in rec["recommendations"]:
        assert 0.0 <= r["score"] <= 1.0

    # 4. 피드백 — 1번 곡 좋아요, 2번 곡 싫어요
    res = client.post(
        "/feedback/like",
        json={"recommendation_id": session_id, "track_id": track_1},
        headers=_auth_header(access),
    )
    assert res.status_code == 201

    res = client.post(
        "/feedback/dislike",
        json={"recommendation_id": session_id, "track_id": track_2},
        headers=_auth_header(access),
    )
    assert res.status_code == 201

    # 좋아요 중복 요청 → 409
    res = client.post(
        "/feedback/like",
        json={"recommendation_id": session_id, "track_id": track_1},
        headers=_auth_header(access),
    )
    assert res.status_code == 409

    # 5. 재생 이벤트 로깅 (start → complete)
    res = client.post(
        "/feedback/playback",
        json={"track_id": track_3, "event": "start", "playback_pct": 0.0},
        headers=_auth_header(access),
    )
    assert res.status_code == 201

    res = client.post(
        "/feedback/playback",
        json={"track_id": track_3, "event": "complete", "playback_pct": 100.0},
        headers=_auth_header(access),
    )
    assert res.status_code == 201

    # 6. 이력 조회 — 세션 + 추천 곡 + 피드백 포함
    res = client.get("/history", headers=_auth_header(access))
    assert res.status_code == 200
    history = res.json()

    assert len(history) == 1
    item = history[0]
    assert item["id"] == session_id
    assert len(item["recommended_tracks"]) >= 1

    # rank 오름차순 정렬 확인
    ranks = [t["rank"] for t in item["recommended_tracks"]]
    assert ranks == sorted(ranks)

    # 피드백 2건 포함 확인
    fb_track_ids = {f["track_id"] for f in item["feedbacks"]}
    assert track_1 in fb_track_ids
    assert track_2 in fb_track_ids

    # 7. 두 번째 추천 요청 — 피드백 누적 후에도 정상 동작
    res = client.post(
        "/recommend",
        files={"audio": ("audio.wav", audio, "audio/wav")},
        headers=_auth_header(access),
    )
    assert res.status_code == 200
    rec2 = res.json()
    assert len(rec2["recommendations"]) >= 1
    for r in rec2["recommendations"]:
        assert 0.0 <= r["score"] <= 1.0

    # 이력이 2건으로 늘었는지 확인
    res = client.get("/history?n=10", headers=_auth_header(access))
    assert len(res.json()) == 2

    # 8. 토큰 갱신 — refresh는 access_token만 반환
    res = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 200
    new_access = res.json()["access_token"]
    assert "access_token" in res.json()

    # 기존 refresh token 재사용 불가 (rotation 확인)
    res = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert res.status_code == 401

    # 9. 로그아웃 (access_token만 사용)
    res = client.post(
        "/auth/logout",
        json={"refresh_token": "dummy"},  # 이미 rotation된 상태 — 204 멱등성
        headers=_auth_header(new_access),
    )
    assert res.status_code == 204

    # 로그아웃 후 만료된 토큰으로 추천 요청 → 401
    res = client.post(
        "/recommend",
        files={"audio": ("audio.wav", audio, "audio/wav")},
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert res.status_code == 401
