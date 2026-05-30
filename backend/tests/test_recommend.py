import io
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
import app.models  # noqa: F401
from app.routers.recommend import router
from app.services.ml_client import MLClient, VADResult, get_ml_client
from app.services.stt import get_stt_provider

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
        "id": i + 1,
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


def _make_mock_stt(transcript: str = ""):
    mock = MagicMock()
    mock.transcribe = AsyncMock(return_value=transcript)
    return mock


def _make_mock_ml(valence: float = 0.0, arousal: float = 0.0, dominance: float = 0.0):
    mock = MagicMock(spec=MLClient)
    mock.predict = AsyncMock(return_value=VADResult(
        valence=valence,
        arousal=arousal,
        dominance=dominance,
    ))
    return mock


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
    test_app.dependency_overrides[get_stt_provider] = lambda: _make_mock_stt()
    test_app.dependency_overrides[get_ml_client] = lambda: _make_mock_ml()

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


def test_recommend_stt_transcript_in_response() -> None:
    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    transcript_text = "오늘 기분이 너무 좋아"
    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_stt_provider] = lambda: _make_mock_stt(transcript_text)
    test_app.dependency_overrides[get_ml_client] = lambda: _make_mock_ml()

    with TestClient(test_app) as c:
        res = c.post("/recommend", files=_audio_file())

    assert res.status_code == 200
    assert res.json()["transcript"] == transcript_text


def test_recommend_empty_catalog_returns_empty() -> None:
    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    from app.models.music_catalog import MusicCatalog
    db = TestingSessionLocal()
    db.query(MusicCatalog).delete()
    db.commit()
    db.close()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_stt_provider] = lambda: _make_mock_stt()
    test_app.dependency_overrides[get_ml_client] = lambda: _make_mock_ml()

    with TestClient(test_app) as c:
        res = c.post("/recommend", files=_audio_file())
    assert res.status_code == 200
    assert res.json()["tracks"] == []


def test_recommend_fewer_than_ten_returns_all() -> None:
    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    from app.models.music_catalog import MusicCatalog
    db = TestingSessionLocal()
    db.query(MusicCatalog).delete()
    for i in range(5):
        db.add(MusicCatalog(**_make_catalog_row(i)))
    db.commit()
    db.close()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_stt_provider] = lambda: _make_mock_stt()
    test_app.dependency_overrides[get_ml_client] = lambda: _make_mock_ml()

    with TestClient(test_app) as c:
        res = c.post("/recommend", files=_audio_file())
    assert res.status_code == 200
    assert len(res.json()["tracks"]) == 5


def test_recommend_vad_positive_affects_results() -> None:
    """EmotionFusion 통합 검증 — VAD 값이 라우터를 통해 추천 파이프라인에 전달됨"""
    test_app = FastAPI()
    test_app.include_router(router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_stt_provider] = lambda: _make_mock_stt()
    test_app.dependency_overrides[get_ml_client] = lambda: _make_mock_ml(
        valence=0.8, arousal=0.7, dominance=0.5
    )

    with TestClient(test_app) as c:
        res = c.post("/recommend", files=_audio_file())

    assert res.status_code == 200
    assert len(res.json()["tracks"]) == 10
