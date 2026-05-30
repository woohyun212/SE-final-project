import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
import app.models  # noqa: F401
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationSession
from app.routers.auth import get_current_user
from app.routers.feedback import router

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class _MockUser:
    id = 1
    email = "test@example.com"


def _mock_current_user():
    return _MockUser()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_app(*, with_auth: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _override_get_db
    if with_auth:
        app.dependency_overrides[get_current_user] = _mock_current_user
    return TestClient(app, raise_server_exceptions=False)


def _seed(user_id: int = 1) -> tuple[str, str]:
    """DB에 RecommendationSession + MusicCatalog 생성 후 (session_id, track_id) 반환"""
    db = TestingSessionLocal()
    session = RecommendationSession(user_id=user_id, user_valence=0.5, user_energy=0.5)
    db.add(session)
    db.add(MusicCatalog(
        track_id="track_001",
        id=1,
        track_name="Test Track",
        artists="Artist",
        album_name="Album",
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
    ))
    db.commit()
    sid = session.id
    db.close()
    return sid, "track_001"


def test_like_success() -> None:
    client = _make_app()
    session_id, track_id = _seed()
    res = client.post("/feedback/like", json={"recommendation_id": session_id, "track_id": track_id})
    assert res.status_code == 201


def test_dislike_success() -> None:
    client = _make_app()
    session_id, track_id = _seed()
    res = client.post("/feedback/dislike", json={"recommendation_id": session_id, "track_id": track_id})
    assert res.status_code == 201


def test_like_no_auth() -> None:
    client = _make_app(with_auth=False)
    session_id, track_id = _seed()
    res = client.post("/feedback/like", json={"recommendation_id": session_id, "track_id": track_id})
    assert res.status_code == 401


def test_dislike_no_auth() -> None:
    client = _make_app(with_auth=False)
    session_id, track_id = _seed()
    res = client.post("/feedback/dislike", json={"recommendation_id": session_id, "track_id": track_id})
    assert res.status_code == 401


def test_like_duplicate_returns_409() -> None:
    client = _make_app()
    session_id, track_id = _seed()
    client.post("/feedback/like", json={"recommendation_id": session_id, "track_id": track_id})
    res = client.post("/feedback/like", json={"recommendation_id": session_id, "track_id": track_id})
    assert res.status_code == 409


def test_like_other_user_session_returns_404() -> None:
    client = _make_app()
    # user_id=2 소유 세션 — mock user는 id=1
    session_id, track_id = _seed(user_id=2)
    res = client.post("/feedback/like", json={"recommendation_id": session_id, "track_id": track_id})
    assert res.status_code == 404


def test_like_nonexistent_session_returns_404() -> None:
    client = _make_app()
    res = client.post("/feedback/like", json={
        "recommendation_id": "00000000-0000-0000-0000-000000000000",
        "track_id": "track_001",
    })
    assert res.status_code == 404


def test_like_nonexistent_track_returns_404() -> None:
    client = _make_app()
    session_id, _ = _seed()
    res = client.post("/feedback/like", json={"recommendation_id": session_id, "track_id": "no_such_track"})
    assert res.status_code == 404


# ── playback ──────────────────────────────────────────────────────────────────

def test_playback_success() -> None:
    client = _make_app()
    _, track_id = _seed()
    res = client.post("/feedback/playback", json={
        "track_id": track_id, "event": "start", "playback_pct": 0.0,
    })
    assert res.status_code == 201


def test_playback_complete_with_pct() -> None:
    client = _make_app()
    _, track_id = _seed()
    res = client.post("/feedback/playback", json={
        "track_id": track_id, "event": "complete", "playback_pct": 100.0,
    })
    assert res.status_code == 201


def test_playback_pct_optional() -> None:
    client = _make_app()
    _, track_id = _seed()
    res = client.post("/feedback/playback", json={"track_id": track_id, "event": "end"})
    assert res.status_code == 201


def test_playback_no_auth_returns_401() -> None:
    client = _make_app(with_auth=False)
    _, track_id = _seed()
    res = client.post("/feedback/playback", json={"track_id": track_id, "event": "start"})
    assert res.status_code == 401


def test_playback_invalid_event_returns_422() -> None:
    client = _make_app()
    _, track_id = _seed()
    res = client.post("/feedback/playback", json={"track_id": track_id, "event": "pause"})
    assert res.status_code == 422


def test_playback_pct_out_of_range_returns_422() -> None:
    client = _make_app()
    _, track_id = _seed()
    res = client.post("/feedback/playback", json={
        "track_id": track_id, "event": "complete", "playback_pct": 150.0,
    })
    assert res.status_code == 422


def test_playback_nonexistent_track_returns_404() -> None:
    client = _make_app()
    _seed()
    res = client.post("/feedback/playback", json={"track_id": "no_such_track", "event": "start"})
    assert res.status_code == 404
