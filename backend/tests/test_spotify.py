"""
Spotify service tests — HTTP calls are intercepted via httpx.MockTransport
so no real Spotify credentials are needed.
"""
import time
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import spotify as spotify_svc

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_FAKE_TOKEN_RESP = {"access_token": "fake_token", "expires_in": 3600, "token_type": "Bearer"}

_FAKE_SEARCH_RESP = {
    "tracks": {
        "items": [
            {
                "id": "track123",
                "name": "Test Song",
                "artists": [{"name": "Artist A"}],
                "album": {"name": "Album X"},
                "duration_ms": 210000,
                "preview_url": None,
            }
        ],
        "total": 1,
    }
}

_FAKE_AUDIO_FEATURES = {
    "id": "track123",
    "danceability": 0.8,
    "energy": 0.7,
    "key": 5,
    "loudness": -5.0,
    "mode": 1,
    "speechiness": 0.05,
    "acousticness": 0.1,
    "instrumentalness": 0.0,
    "liveness": 0.12,
    "valence": 0.6,
    "tempo": 120.0,
    "duration_ms": 210000,
}

_FAKE_TRACK = {
    "id": "track123",
    "name": "Test Song",
    "artists": [{"name": "Artist A"}],
    "album": {"name": "Album X"},
    "duration_ms": 210000,
}


def _make_transport(*route_maps: dict[str, dict]) -> httpx.MockTransport:
    """Build a MockTransport that matches URL substrings to response bodies.

    Each map in route_maps is checked in order; the first matching prefix wins.
    Token endpoint (accounts.spotify.com) always returns _FAKE_TOKEN_RESP.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "accounts.spotify.com" in url:
            return httpx.Response(200, json=_FAKE_TOKEN_RESP)
        for routes in route_maps:
            for prefix, body in routes.items():
                if prefix in url:
                    status = body.pop("__status__", 200)
                    resp = httpx.Response(status, json=body)
                    if status != 200:
                        body["__status__"] = status  # restore for reuse
                    return resp
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


def _patched_client(transport: httpx.MockTransport):
    """Context manager: replace httpx.AsyncClient with one using mock transport."""
    _real = httpx.AsyncClient

    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _real(transport=transport, **kwargs)

    return patch("httpx.AsyncClient", factory)


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_access_token_caches():
    """Token is cached and not re-fetched on second call within TTL."""
    spotify_svc._token_cache["access_token"] = None
    spotify_svc._token_cache["expires_at"] = 0.0

    transport = _make_transport()
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            token1 = await spotify_svc._get_access_token()
            token2 = await spotify_svc._get_access_token()

    assert token1 == token2 == "fake_token"


@pytest.mark.anyio
async def test_get_access_token_refreshes_when_expired():
    spotify_svc._token_cache["access_token"] = "old_token"
    spotify_svc._token_cache["expires_at"] = time.time() - 1

    transport = _make_transport()
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            token = await spotify_svc._get_access_token()

    assert token == "fake_token"


@pytest.mark.anyio
async def test_search_tracks_returns_parsed_result():
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    transport = _make_transport({"/search": _FAKE_SEARCH_RESP})
    with _patched_client(transport):
        result = await spotify_svc.search_tracks("happy", limit=5)

    assert result["total"] == 1
    assert result["tracks"][0]["track_id"] == "track123"
    assert result["tracks"][0]["artists"] == ["Artist A"]


@pytest.mark.anyio
async def test_search_tracks_rate_limit_raises():
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={}, headers={"Retry-After": "5"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with pytest.raises(spotify_svc.RateLimitError) as exc_info:
            await spotify_svc.search_tracks("happy")

    assert exc_info.value.retry_after == 5


@pytest.mark.anyio
async def test_get_audio_features_merges_data():
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "audio-features" in url:
            return httpx.Response(200, json=_FAKE_AUDIO_FEATURES)
        if "/tracks/" in url:
            return httpx.Response(200, json=_FAKE_TRACK)
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        result = await spotify_svc.get_audio_features("track123")

    assert result["track_id"] == "track123"
    assert result["name"] == "Test Song"
    assert result["danceability"] == 0.8
    assert result["tempo"] == 120.0


# ---------------------------------------------------------------------------
# Router / integration tests (no real Spotify calls)
# ---------------------------------------------------------------------------

def test_search_endpoint_missing_credentials(monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    spotify_svc._token_cache["access_token"] = None
    spotify_svc._token_cache["expires_at"] = 0.0

    response = client.get("/spotify/search?q=happy")
    assert response.status_code == 503


def test_audio_features_endpoint_missing_credentials(monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    spotify_svc._token_cache["access_token"] = None
    spotify_svc._token_cache["expires_at"] = 0.0

    response = client.get("/spotify/audio-features/track123")
    assert response.status_code == 503
