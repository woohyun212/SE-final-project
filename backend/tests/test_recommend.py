"""Tests for /recommend endpoint (US-8: emotion vector → Spotify similarity matching)."""

import io
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.recommend import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _audio_file(filename: str = "test.wav") -> dict:
    return {"audio": (filename, io.BytesIO(b"dummy-audio-data"), "audio/wav")}


_MOCK_CATALOG = [
    {
        "track_id": f"track{i}",
        "name": f"Song {i}",
        "artists": [f"Artist {i}"],
        "album": f"Album {i}",
        "duration_ms": 200_000,
        "preview_url": None,
    }
    for i in range(15)
]

_MOCK_FEATURES = {
    f"track{i}": {
        "danceability": 0.5 + i * 0.01,
        "energy": 0.6,
        "valence": 0.7,
        "acousticness": 0.2,
        "instrumentalness": 0.1,
    }
    for i in range(15)
}


def _patch_recommend():
    """Patch both Spotify-bound helpers used by recommend_by_emotion."""
    build = patch(
        "app.services.recommendation._build_catalog",
        new_callable=AsyncMock,
        return_value=_MOCK_CATALOG,
    )
    features = patch(
        "app.services.recommendation._get_batch_audio_features",
        new_callable=AsyncMock,
        return_value=_MOCK_FEATURES,
    )
    return build, features


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_recommend_returns_ten_tracks() -> None:
    build, features = _patch_recommend()
    with build, features:
        res = client.post("/recommend", files=_audio_file())
    assert res.status_code == 200
    assert len(res.json()["tracks"]) == 10


def test_recommend_track_schema() -> None:
    build, features = _patch_recommend()
    with build, features:
        res = client.post("/recommend", files=_audio_file())
    for track in res.json()["tracks"]:
        assert "title" in track
        assert "artist" in track
        assert "album" in track
        assert "duration_sec" in track
        assert isinstance(track["duration_sec"], int)


def test_recommend_response_time() -> None:
    build, features = _patch_recommend()
    with build, features:
        start = time.perf_counter()
        res = client.post("/recommend", files=_audio_file())
        elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed < 1.0, f"응답 시간 초과: {elapsed:.3f}s"


@pytest.mark.parametrize("emotion", ["happy", "sad", "angry", "relaxed", "anxious", "neutral"])
def test_recommend_all_emotions(emotion: str) -> None:
    build, features = _patch_recommend()
    with build, features:
        res = client.post("/recommend", files=_audio_file(), params={"emotion": emotion})
    assert res.status_code == 200
    assert len(res.json()["tracks"]) > 0


def test_recommend_unknown_emotion_falls_back_to_neutral() -> None:
    """Unknown emotion label silently falls back to neutral vector."""
    build, features = _patch_recommend()
    with build, features:
        res = client.post("/recommend", files=_audio_file(), params={"emotion": "confused"})
    assert res.status_code == 200


def test_recommend_empty_catalog_returns_empty_list() -> None:
    build = patch(
        "app.services.recommendation._build_catalog",
        new_callable=AsyncMock,
        return_value=[],
    )
    features = patch(
        "app.services.recommendation._get_batch_audio_features",
        new_callable=AsyncMock,
        return_value={},
    )
    with build, features:
        res = client.post("/recommend", files=_audio_file())
    assert res.status_code == 200
    assert res.json()["tracks"] == []
