import io
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.recommend import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _audio_file(filename: str = "test.wav") -> dict:
    return {"audio": (filename, io.BytesIO(b"dummy-audio-data"), "audio/wav")}


def test_recommend_returns_five_tracks() -> None:
    res = client.post("/recommend", files=_audio_file())
    assert res.status_code == 200
    body = res.json()
    assert len(body["tracks"]) == 5


def test_recommend_track_schema() -> None:
    res = client.post("/recommend", files=_audio_file())
    for track in res.json()["tracks"]:
        assert "title" in track
        assert "artist" in track
        assert "album" in track
        assert "duration_sec" in track
        assert isinstance(track["duration_sec"], int)


def test_recommend_response_time() -> None:
    start = time.perf_counter()
    res = client.post("/recommend", files=_audio_file())
    elapsed = time.perf_counter() - start
    assert res.status_code == 200
    assert elapsed < 1.0, f"응답 시간 초과: {elapsed:.3f}s"
