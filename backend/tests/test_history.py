import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.models.feedback import Feedback, FeedbackType
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationSession
from app.routers.auth import get_current_user
from app.routers.history import router

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


def _seed_session(user_id: int = 1, *, valence: float = 0.5, energy: float = 0.5) -> str:
    db = TestingSessionLocal()
    session = RecommendationSession(user_id=user_id, user_valence=valence, user_energy=energy)
    db.add(session)
    db.commit()
    sid = session.id
    db.close()
    return sid


def _seed_feedback(session_id: str, track_id: str, i: int, user_id: int = 1) -> None:
    db = TestingSessionLocal()
    if db.get(MusicCatalog, track_id) is None:
        db.add(_make_track(track_id, i))
    db.add(Feedback(
        user_id=user_id,
        track_id=track_id,
        recommendation_id=session_id,
        feedback_type=FeedbackType.like,
    ))
    db.commit()
    db.close()


def test_history_no_auth_returns_401() -> None:
    client = _make_app(with_auth=False)
    res = client.get("/history")
    assert res.status_code == 401


def test_history_empty_returns_empty_list() -> None:
    client = _make_app()
    res = client.get("/history")
    assert res.status_code == 200
    assert res.json() == []


def test_history_returns_sessions_desc() -> None:
    client = _make_app()
    s1 = _seed_session()
    s2 = _seed_session()
    res = client.get("/history")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 2
    # 최신순 — 마지막에 만든 s2 가 먼저
    assert body[0]["id"] == s2
    assert body[1]["id"] == s1
    assert body[0]["feedbacks"] == []


def test_history_includes_feedback_tracks() -> None:
    client = _make_app()
    sid = _seed_session(valence=0.7, energy=0.6)
    _seed_feedback(sid, "track_001", 1)
    _seed_feedback(sid, "track_002", 2)
    res = client.get("/history")
    assert res.status_code == 200
    item = res.json()[0]
    assert item["id"] == sid
    assert item["user_valence"] == 0.7
    assert len(item["feedbacks"]) == 2
    track_ids = {f["track_id"] for f in item["feedbacks"]}
    assert track_ids == {"track_001", "track_002"}
    assert item["feedbacks"][0]["feedback_type"] == "like"


def test_history_excludes_other_users_sessions() -> None:
    client = _make_app()
    _seed_session(user_id=2)  # 타인 세션
    own = _seed_session(user_id=1)
    res = client.get("/history")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["id"] == own


def test_history_respects_n_limit() -> None:
    client = _make_app()
    for _ in range(5):
        _seed_session()
    res = client.get("/history?n=3")
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_history_rejects_invalid_n() -> None:
    client = _make_app()
    assert client.get("/history?n=0").status_code == 422
    assert client.get("/history?n=51").status_code == 422
