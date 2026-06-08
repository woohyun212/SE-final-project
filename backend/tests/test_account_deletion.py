"""FR1.4 계정 탈퇴 (#180) — DELETE /auth/me 영구 삭제 테스트."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.models.feedback import Feedback, FeedbackType, PlaybackEvent
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationResult, RecommendationSession
from app.models.token import RefreshToken
from app.models.user import User
from app.models.user_preference import UserPreference
from app.routers.auth import router

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as c:
        yield c


# ── helpers ──────────────────────────────────────────────────────────────────

def _signup(client: TestClient, email: str = "test@example.com", password: str = "Password1") -> dict:
    res = client.post("/auth/signup", json={"email": email, "password": password})
    assert res.status_code == 201
    return res.json()


def _auth_header(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _user_id_by_email(email: str) -> int:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.close()
    assert user is not None
    return user.id


def _make_track(track_id: str, i: int) -> MusicCatalog:
    return MusicCatalog(
        track_id=track_id,
        id=i,
        track_name=f"Track {i}",
        artists=f"Artist {i}",
        album_name=f"Album {i}",
        track_genre="pop",
        popularity=50,
        duration_ms=200_000,
        danceability=0.5,
        energy=0.5,
        valence=0.5,
        acousticness=0.1,
        instrumentalness=0.0,
        speechiness=0.05,
        liveness=0.1,
        tempo=120.0,
        loudness=-8.0,
        key=0,
        mode=1,
        time_signature=4,
    )


def _seed_personal_data(user_id: int, *, track_id: str = "track_001", track_seq: int = 1) -> str:
    """유저의 개인 데이터(세션·추천결과·피드백·재생이벤트·선호도)를 시드하고 session_id 반환."""
    db = TestingSessionLocal()
    if db.get(MusicCatalog, track_id) is None:
        db.add(_make_track(track_id, track_seq))
    session = RecommendationSession(user_id=user_id, user_valence=0.5, user_energy=0.5)
    db.add(session)
    db.flush()
    db.add(RecommendationResult(session_id=session.id, track_id=track_id, rank=1, score=0.9))
    db.add(Feedback(
        user_id=user_id,
        track_id=track_id,
        recommendation_id=session.id,
        feedback_type=FeedbackType.like,
    ))
    db.add(PlaybackEvent(user_id=user_id, track_id=track_id, event="start", playback_pct=0.0))
    db.add(UserPreference(user_id=user_id))
    db.commit()
    sid = session.id
    db.close()
    return sid


def _count(model, **filters) -> int:
    db = TestingSessionLocal()
    n = db.query(model).filter_by(**filters).count()
    db.close()
    return n


# ── DELETE /auth/me ───────────────────────────────────────────────────────────

def test_delete_me_returns_204_and_removes_user(client: TestClient) -> None:
    tokens = _signup(client)
    user_id = _user_id_by_email("test@example.com")

    res = client.delete("/auth/me", headers=_auth_header(tokens))
    assert res.status_code == 204

    db = TestingSessionLocal()
    assert db.get(User, user_id) is None  # 소프트삭제(is_active)가 아닌 영구 삭제
    db.close()


def test_delete_me_requires_auth(client: TestClient) -> None:
    _signup(client)
    res = client.delete("/auth/me")
    assert res.status_code == 401


def test_delete_me_purges_all_personal_data(client: TestClient) -> None:
    tokens = _signup(client)
    user_id = _user_id_by_email("test@example.com")
    session_id = _seed_personal_data(user_id)

    res = client.delete("/auth/me", headers=_auth_header(tokens))
    assert res.status_code == 204

    assert _count(Feedback, user_id=user_id) == 0
    assert _count(PlaybackEvent, user_id=user_id) == 0
    assert _count(RecommendationResult, session_id=session_id) == 0
    assert _count(RecommendationSession, user_id=user_id) == 0
    assert _count(RefreshToken, user_id=user_id) == 0
    assert _count(UserPreference, user_id=user_id) == 0


def test_delete_me_keeps_other_users_data(client: TestClient) -> None:
    tokens_a = _signup(client, email="a@example.com")
    _signup(client, email="b@example.com")
    user_a = _user_id_by_email("a@example.com")
    user_b = _user_id_by_email("b@example.com")
    _seed_personal_data(user_a, track_id="track_001", track_seq=1)
    session_b = _seed_personal_data(user_b, track_id="track_002", track_seq=2)

    res = client.delete("/auth/me", headers=_auth_header(tokens_a))
    assert res.status_code == 204

    db = TestingSessionLocal()
    assert db.get(User, user_b) is not None
    db.close()
    assert _count(Feedback, user_id=user_b) == 1
    assert _count(PlaybackEvent, user_id=user_b) == 1
    assert _count(RecommendationResult, session_id=session_b) == 1
    assert _count(RecommendationSession, user_id=user_b) == 1
    assert _count(RefreshToken, user_id=user_b) == 1
    assert _count(UserPreference, user_id=user_b) == 1


def test_deleted_user_access_token_rejected(client: TestClient) -> None:
    tokens = _signup(client)
    assert client.delete("/auth/me", headers=_auth_header(tokens)).status_code == 204
    # 같은 access token 재사용 — 사용자 조회 실패로 401
    res = client.delete("/auth/me", headers=_auth_header(tokens))
    assert res.status_code == 401


def test_deleted_user_refresh_token_rejected(client: TestClient) -> None:
    tokens = _signup(client)
    assert client.delete("/auth/me", headers=_auth_header(tokens)).status_code == 204
    res = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert res.status_code == 401


def test_email_reusable_after_deletion(client: TestClient) -> None:
    tokens = _signup(client)
    assert client.delete("/auth/me", headers=_auth_header(tokens)).status_code == 204
    # 영구 삭제이므로 동일 이메일 재가입 가능
    res = client.post("/auth/signup", json={"email": "test@example.com", "password": "Password1"})
    assert res.status_code == 201
