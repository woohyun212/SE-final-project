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


@pytest.fixture(autouse=True)
def reset_spotify_state():
    """Reset module-level state between tests to prevent leakage."""
    spotify_svc._token_cache["access_token"] = None
    spotify_svc._token_cache["expires_at"] = 0.0
    original_client = spotify_svc._http_client
    yield
    spotify_svc._http_client = original_client


def _make_transport(*route_maps: dict) -> httpx.MockTransport:
    """Build a MockTransport that matches URL substrings to canned responses.

    Each map entry: {url_prefix: {"__status__": <int>, ...body...}}
    Status defaults to 200 when __status__ is absent.
    Token endpoint always returns _FAKE_TOKEN_RESP.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "accounts.spotify.com" in url:
            return httpx.Response(200, json=_FAKE_TOKEN_RESP)
        for routes in route_maps:
            for prefix, body in routes.items():
                if prefix in url:
                    body = dict(body)  # copy so originals are never mutated
                    status_code = body.pop("__status__", 200)
                    return httpx.Response(status_code, json=body)
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


def _patched_client(transport: httpx.MockTransport):
    """Context manager: replace module-level HTTP client with a mock."""
    mock = httpx.AsyncClient(transport=transport, timeout=10)
    return patch.object(spotify_svc, "_http_client", mock)


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------

async def test_get_access_token_caches():
    """Token is cached and not re-fetched on second call within TTL."""
    transport = _make_transport()
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            token1 = await spotify_svc._get_access_token()
            token2 = await spotify_svc._get_access_token()

    assert token1 == token2 == "fake_token"


async def test_get_access_token_refreshes_when_expired():
    spotify_svc._token_cache["access_token"] = "old_token"
    spotify_svc._token_cache["expires_at"] = time.time() - 1

    transport = _make_transport()
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            token = await spotify_svc._get_access_token()

    assert token == "fake_token"


async def test_search_tracks_returns_parsed_result():
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    transport = _make_transport({"/search": _FAKE_SEARCH_RESP})
    with _patched_client(transport):
        result = await spotify_svc.search_tracks("happy", limit=5)

    assert result["total"] == 1
    assert result["tracks"][0]["track_id"] == "track123"
    assert result["tracks"][0]["artists"] == ["Artist A"]


async def test_search_tracks_empty_results():
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    empty_resp = {"tracks": {"items": [], "total": 0}}
    transport = _make_transport({"/search": empty_resp})
    with _patched_client(transport):
        result = await spotify_svc.search_tracks("xyzzy_no_match")

    assert result["total"] == 0
    assert result["tracks"] == []


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


async def test_audio_features_rate_limit_raises():
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={}, headers={"Retry-After": "3"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with pytest.raises(spotify_svc.RateLimitError) as exc_info:
            await spotify_svc.get_audio_features("track123")

    assert exc_info.value.retry_after == 3


async def test_audio_features_not_found_raises():
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with pytest.raises(spotify_svc.SpotifyNotFoundError):
            await spotify_svc.get_audio_features("nonexistent_id")


# ---------------------------------------------------------------------------
# Router / integration tests (no real Spotify calls)
# ---------------------------------------------------------------------------

def test_search_endpoint_missing_credentials(monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    response = client.get("/spotify/search?q=happy")
    assert response.status_code == 503


def test_audio_features_endpoint_missing_credentials(monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    response = client.get("/spotify/audio-features/track123")
    assert response.status_code == 503


def test_audio_features_endpoint_not_found():
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        response = client.get("/spotify/audio-features/bad_id")

    assert response.status_code == 404
