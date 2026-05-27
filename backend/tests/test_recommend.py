import io
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
import app.models  # noqa: F401
from app.routers.recommend import router

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _make_catalog_row(i: int, **overrides) -> dict:
    base = {
        "track_id": f"track_{i:03d}",
        "track_name": f"Track {i}",
        "artists": f"Artist {i}",
        "album_name": f"Album {i}",
        "track_genre": "pop",
        "popularity": 50,
        "duration_ms": 200_000 + i * 1_000,
        "preview_url": None,
        "danceability": round(0.1 + (i % 9) * 0.1, 1),
        "energy": round(0.1 + (i % 8) * 0.1, 1),
        "valence": round(0.1 + (i % 7) * 0.1, 1),
        "acousticness": round(0.05 * (i % 10), 2),
        "instrumentalness": round(0.02 * (i % 5), 2),
        "speechiness": 0.05,
        "liveness": 0.1,
        "tempo": 120.0,
        "loudness": -8.0,
        "key": 0,
        "mode": 1,
        "time_signature": 4,
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    from app.models.music_catalog import MusicCatalog

    db = TestingSessionLocal()
    for i in range(12):
        db.add(MusicCatalog(**_make_catalog_row(i)))
    db.commit()
    db.close()
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


def _audio_file(filename: str = "test.wav") -> dict:
    return {"audio": (filename, io.BytesIO(b"dummy-audio-data"), "audio/wav")}


def test_recommend_returns_ten_tracks(client: TestClient) -> None:
    res = client.post("/recommend", files=_audio_file())
    assert res.status_code == 200
    assert len(res.json()["tracks"]) == 10


def test_recommend_track_schema(client: TestClient) -> None:
    res = client.post("/recommend", files=_audio_file())
    for track in res.json()["tracks"]:
        assert "track_id" in track
        assert "title" in track
        assert "artist" in track
        assert "album" in track
        assert "duration_sec" in track
        assert isinstance(track["duration_sec"], int)


def test_recommend_response_time(client: TestClient) -> None:
    start = time.perf_counter()
    res = client.post("/recommend", files=_audio_file())
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed < 3.0, f"응답 시간 초과: {elapsed:.3f}s"


def test_recommend_with_emotion_params(client: TestClient) -> None:
    res = client.post(
        "/recommend",
        files=_audio_file(),
        data={
            "valence": "0.9",
            "energy": "0.8",
            "danceability": "0.7",
            "acousticness": "0.1",
            "instrumentalness": "0.0",
        },
    )
    assert res.status_code == 200
    assert len(res.json()["tracks"]) == 10


def test_recommend_empty_catalog_returns_empty(client: TestClient) -> None:
    from app.models.music_catalog import MusicCatalog

    db = TestingSessionLocal()
    db.query(MusicCatalog).delete()
    db.commit()
    db.close()

    res = client.post("/recommend", files=_audio_file())
    assert res.status_code == 200
    assert res.json()["tracks"] == []


def test_recommend_fewer_than_ten_returns_all(client: TestClient) -> None:
    from app.models.music_catalog import MusicCatalog

    db = TestingSessionLocal()
    db.query(MusicCatalog).delete()
    for i in range(5):
        db.add(MusicCatalog(**_make_catalog_row(i)))
    db.commit()
    db.close()

    res = client.post("/recommend", files=_audio_file())
    assert res.status_code == 200
    assert len(res.json()["tracks"]) == 5
