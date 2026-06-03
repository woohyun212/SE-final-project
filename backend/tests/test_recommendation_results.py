"""recommendation_results 저장 및 GET /history recommended_tracks 포함 검증."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationResult, RecommendationSession
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


def _make_app() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _override_get_db
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


def _seed_session_with_results(
    tracks: list[tuple[str, int, float]],
    user_id: int = 1,
) -> str:
    """세션 생성 후 (track_id, catalog_i, score) 목록으로 recommendation_results 저장."""
    db = TestingSessionLocal()
    session = RecommendationSession(user_id=user_id, user_valence=0.5, user_energy=0.5)
    db.add(session)
    db.flush()
    for rank, (track_id, catalog_i, score) in enumerate(tracks, start=1):
        if db.get(MusicCatalog, track_id) is None:
            db.add(_make_track(track_id, catalog_i))
        db.add(RecommendationResult(
            session_id=session.id,
            track_id=track_id,
            rank=rank,
            score=score,
        ))
    db.commit()
    sid = session.id
    db.close()
    return sid


def test_recommended_tracks_saved_and_returned() -> None:
    """추천 결과 곡이 DB에 저장되고 GET /history 응답에 포함된다."""
    client = _make_app()
    sid = _seed_session_with_results([
        ("track_001", 1, 0.95),
        ("track_002", 2, 0.87),
        ("track_003", 3, 0.72),
    ])
    res = client.get("/history")
    assert res.status_code == 200
    item = res.json()[0]
    assert item["id"] == sid
    assert len(item["recommended_tracks"]) == 3


def test_recommended_tracks_rank_and_score() -> None:
    """추천 결과의 rank, score, track_id 값이 정확히 반환된다."""
    client = _make_app()
    _seed_session_with_results([
        ("track_a", 10, 0.91),
        ("track_b", 11, 0.83),
    ])
    res = client.get("/history")
    tracks = res.json()[0]["recommended_tracks"]
    assert tracks[0]["rank"] == 1
    assert tracks[0]["track_id"] == "track_a"
    assert tracks[0]["score"] == pytest.approx(0.91)
    assert tracks[1]["rank"] == 2
    assert tracks[1]["track_id"] == "track_b"


def test_recommended_tracks_ordered_by_rank() -> None:
    """recommended_tracks는 rank 오름차순으로 반환된다."""
    client = _make_app()
    _seed_session_with_results([
        ("track_x", 20, 0.80),
        ("track_y", 21, 0.90),
        ("track_z", 22, 0.70),
    ])
    res = client.get("/history")
    tracks = res.json()[0]["recommended_tracks"]
    ranks = [t["rank"] for t in tracks]
    assert ranks == sorted(ranks)


def test_recommended_tracks_empty_when_none_saved() -> None:
    """추천 결과가 없는 세션은 recommended_tracks가 빈 리스트다."""
    client = _make_app()
    db = TestingSessionLocal()
    session = RecommendationSession(user_id=1, user_valence=0.5, user_energy=0.5)
    db.add(session)
    db.commit()
    db.close()

    res = client.get("/history")
    assert res.status_code == 200
    assert res.json()[0]["recommended_tracks"] == []


def test_recommended_tracks_isolated_between_sessions() -> None:
    """각 세션의 recommended_tracks는 해당 세션 곡만 포함한다."""
    client = _make_app()
    sid1 = _seed_session_with_results([("track_s1", 30, 0.9)])
    sid2 = _seed_session_with_results([("track_s2", 31, 0.8), ("track_s3", 32, 0.7)])

    res = client.get("/history")
    items = {item["id"]: item for item in res.json()}
    assert len(items[sid1]["recommended_tracks"]) == 1
    assert len(items[sid2]["recommended_tracks"]) == 2
    assert items[sid1]["recommended_tracks"][0]["track_id"] == "track_s1"
