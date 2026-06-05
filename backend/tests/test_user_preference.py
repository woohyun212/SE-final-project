"""
Tests for UserPreference incremental update and recommendation profile lookup.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationSession
from app.models.user_preference import UserPreference, _FEATURE_COLS
from app.routers.auth import get_current_user
from app.routers.feedback import router as feedback_router
from app.services.recommendation import recommend_by_emotion

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
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


def _make_feedback_client() -> TestClient:
    app = FastAPI()
    app.include_router(feedback_router)
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _mock_current_user
    return TestClient(app, raise_server_exceptions=False)


def _seed_track(
    track_id: str = "track_001",
    danceability: float = 0.6,
    energy: float = 0.7,
    valence: float = 0.8,
    acousticness: float = 0.1,
    instrumentalness: float = 0.05,
) -> MusicCatalog:
    db = TestingSessionLocal()
    track = MusicCatalog(
        track_id=track_id,
        id=abs(hash(track_id)) % 10_000 + 1,
        track_name=f"Track {track_id}",
        artists="Artist",
        album_name="Album",
        track_genre="pop",
        popularity=50,
        duration_ms=200_000,
        danceability=danceability,
        energy=energy,
        valence=valence,
        acousticness=acousticness,
        instrumentalness=instrumentalness,
        speechiness=0.05,
        liveness=0.1,
        tempo=120.0,
        loudness=-8.0,
        key=0,
        mode=1,
        time_signature=4,
    )
    db.add(track)
    db.commit()
    db.close()
    return track


def _seed_session(user_id: int = 1, session_id: str | None = None) -> str:
    db = TestingSessionLocal()
    session = RecommendationSession(user_id=user_id, user_valence=0.5, user_energy=0.5)
    if session_id:
        session.id = session_id
    db.add(session)
    db.commit()
    sid = session.id
    db.close()
    return sid


# ── incremental update tests ───────────────────────────────────────────────────

def test_like_creates_user_preference():
    """좋아요 후 UserPreference 행이 생성된다."""
    _seed_track("t1", danceability=0.6, energy=0.7, valence=0.8, acousticness=0.1, instrumentalness=0.05)
    sid = _seed_session()
    client = _make_feedback_client()
    res = client.post("/feedback/like", json={"recommendation_id": sid, "track_id": "t1"})
    assert res.status_code == 201

    db = TestingSessionLocal()
    pref = db.get(UserPreference, 1)
    db.close()
    assert pref is not None
    assert pref.like_count == 1
    assert abs(pref.like_danceability - 0.6) < 1e-6
    assert abs(pref.like_energy - 0.7) < 1e-6


def test_dislike_creates_user_preference():
    """싫어요 후 UserPreference 행이 생성된다."""
    _seed_track("t1", danceability=0.3, energy=0.2, valence=0.1, acousticness=0.9, instrumentalness=0.8)
    sid = _seed_session()
    client = _make_feedback_client()
    res = client.post("/feedback/dislike", json={"recommendation_id": sid, "track_id": "t1"})
    assert res.status_code == 201

    db = TestingSessionLocal()
    pref = db.get(UserPreference, 1)
    db.close()
    assert pref is not None
    assert pref.dislike_count == 1
    assert abs(pref.dislike_danceability - 0.3) < 1e-6


def test_incremental_mean_two_likes():
    """두 트랙을 좋아요할 때 평균이 정확하게 갱신된다."""
    _seed_track("t1", danceability=0.4, energy=0.4, valence=0.4, acousticness=0.4, instrumentalness=0.4)
    _seed_track("t2", danceability=0.8, energy=0.8, valence=0.8, acousticness=0.8, instrumentalness=0.8)
    sid1 = _seed_session()
    sid2 = _seed_session()
    client = _make_feedback_client()
    client.post("/feedback/like", json={"recommendation_id": sid1, "track_id": "t1"})
    client.post("/feedback/like", json={"recommendation_id": sid2, "track_id": "t2"})

    db = TestingSessionLocal()
    pref = db.get(UserPreference, 1)
    db.close()
    assert pref.like_count == 2
    # mean of [0.4, 0.8] = 0.6
    assert abs(pref.like_danceability - 0.6) < 1e-6
    assert abs(pref.like_valence - 0.6) < 1e-6


def test_like_and_dislike_independent():
    """좋아요·싫어요 벡터가 서로 독립적으로 갱신된다."""
    _seed_track("t1", danceability=0.9, energy=0.9, valence=0.9, acousticness=0.9, instrumentalness=0.9)
    _seed_track("t2", danceability=0.1, energy=0.1, valence=0.1, acousticness=0.1, instrumentalness=0.1)
    sid1 = _seed_session()
    sid2 = _seed_session()
    client = _make_feedback_client()
    client.post("/feedback/like", json={"recommendation_id": sid1, "track_id": "t1"})
    client.post("/feedback/dislike", json={"recommendation_id": sid2, "track_id": "t2"})

    db = TestingSessionLocal()
    pref = db.get(UserPreference, 1)
    db.close()
    assert pref.like_count == 1
    assert pref.dislike_count == 1
    assert abs(pref.like_danceability - 0.9) < 1e-6
    assert abs(pref.dislike_danceability - 0.1) < 1e-6


# ── recommendation profile lookup tests ───────────────────────────────────────

def test_recommend_cold_start_score_in_range():
    """프로필 없는 cold start — score ∈ [0.0, 1.0]."""
    for i in range(5):
        _seed_track(f"tr{i}", danceability=0.2 * i, energy=0.2 * i,
                    valence=0.2 * i, acousticness=0.1 * i, instrumentalness=0.05 * i)
    db = TestingSessionLocal()
    emotion = {"danceability": 0.5, "energy": 0.5, "valence": 0.5, "acousticness": 0.2, "instrumentalness": 0.1}
    results = recommend_by_emotion(db, emotion, user_id=None)
    db.close()
    for _, score in results:
        assert 0.0 <= score <= 1.0, f"score {score} out of [0, 1]"


def test_recommend_warm_user_score_capped():
    """좋아요 피드백이 있는 warm user — score가 1.0을 초과하지 않는다."""
    _seed_track("t1", danceability=1.0, energy=1.0, valence=1.0, acousticness=0.0, instrumentalness=0.0)
    _seed_track("t2", danceability=0.9, energy=0.9, valence=0.9, acousticness=0.1, instrumentalness=0.0)

    db = TestingSessionLocal()
    # 수동으로 UserPreference 삽입 (like_count=5, like_vec ≈ t1 features)
    from datetime import UTC, datetime
    pref = UserPreference(
        user_id=99,
        like_danceability=1.0,
        like_energy=1.0,
        like_valence=1.0,
        like_acousticness=0.0,
        like_instrumentalness=0.0,
        like_count=5,
        updated_at=datetime.now(UTC),
    )
    db.add(pref)
    db.commit()

    emotion = {"danceability": 1.0, "energy": 1.0, "valence": 1.0, "acousticness": 0.0, "instrumentalness": 0.0}
    results = recommend_by_emotion(db, emotion, user_id=99)
    db.close()

    for _, score in results:
        assert score <= 1.0, f"score {score} exceeds 1.0"


def test_recommend_no_profile_cold_start_path():
    """UserPreference 행이 없는 user_id — cold start로 처리되어 정상 동작한다."""
    _seed_track("t1")
    db = TestingSessionLocal()
    emotion = {"danceability": 0.5, "energy": 0.5, "valence": 0.5, "acousticness": 0.2, "instrumentalness": 0.1}
    results = recommend_by_emotion(db, emotion, user_id=999)  # 존재하지 않는 user_id
    db.close()
    assert len(results) == 1
    _, score = results[0]
    assert 0.0 <= score <= 1.0
