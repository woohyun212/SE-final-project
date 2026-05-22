import asyncio
import os
import time
import logging
from typing import TypedDict

import httpx

logger = logging.getLogger(__name__)

_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SPOTIFY_API_BASE = "https://api.spotify.com/v1"


class _TokenCache(TypedDict):
    access_token: str | None
    expires_at: float


_token_cache: _TokenCache = {"access_token": None, "expires_at": 0.0}
_token_lock = asyncio.Lock()
# Shared HTTP client — reuses connection pool across requests.
# TODO: in multi-worker deployments, token cache is per-worker; migrate to Redis or similar.
_http_client: httpx.AsyncClient | None = None


class SpotifyCredentialsError(RuntimeError):
    """Raised when Spotify API credentials are missing from environment."""


class SpotifyNotFoundError(Exception):
    """Raised when Spotify returns 404 for a requested resource."""


class RateLimitError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Spotify rate limit hit — retry after {retry_after}s")


def _get_credentials() -> tuple[str, str]:
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise SpotifyCredentialsError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")
    return client_id, client_secret


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10)
    return _http_client


async def init_http_client() -> None:
    """Create the shared HTTP client. Call from FastAPI lifespan startup."""
    global _http_client
    _http_client = httpx.AsyncClient(timeout=10)


async def close_http_client() -> None:
    """Close the shared HTTP client. Call from FastAPI lifespan shutdown."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def _get_access_token() -> str:
    """Client Credentials Flow — token is cached until 60 s before expiry."""
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    async with _token_lock:
        now = time.time()  # re-check after acquiring lock to avoid duplicate refresh
        if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
            return _token_cache["access_token"]

        client_id, client_secret = _get_credentials()
        resp = await _get_http_client().post(
            _SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = now + data["expires_in"]
        logger.debug("Spotify token refreshed, expires in %ds", data["expires_in"])
        return _token_cache["access_token"]


async def _spotify_get(path: str, params: dict | None = None) -> dict:
    token = await _get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = await _get_http_client().get(
        f"{_SPOTIFY_API_BASE}{path}",
        headers=headers,
        params=params,
    )
    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", "1"))
        raise RateLimitError(retry_after)
    if resp.status_code == 404:
        raise SpotifyNotFoundError(f"Resource not found: {path}")
    resp.raise_for_status()
    return resp.json()


def _parse_track(item: dict) -> dict:
    return {
        "track_id": item["id"],
        "name": item["name"],
        "artists": [a["name"] for a in item["artists"]],
        "album": item["album"]["name"],
        "duration_ms": item["duration_ms"],
        "preview_url": item.get("preview_url"),
    }


async def search_tracks(query: str, limit: int = 10, offset: int = 0) -> dict:
    """Search Spotify tracks. Returns list of track summaries + total count."""
    data = await _spotify_get(
        "/search",
        params={"q": query, "type": "track", "limit": limit, "offset": offset},
    )
    tracks_data = data["tracks"]
    return {
        "tracks": [_parse_track(t) for t in tracks_data["items"]],
        "total": tracks_data["total"],
    }


async def get_audio_features(track_id: str) -> dict:
    """Fetch audio features for a single track and merge with track metadata.

    NOTE: audio-features is deprecated for Spotify apps created after 2024-11-27.
    Verify the app predates this cutoff and holds a quota extension before deploying.
    """
    features_data, track_data = await _fetch_features_and_track(track_id)
    return {
        "track_id": track_id,
        "name": track_data["name"],
        "artists": [a["name"] for a in track_data["artists"]],
        "album": track_data["album"]["name"],
        "duration_ms": track_data["duration_ms"],
        "danceability": features_data["danceability"],
        "energy": features_data["energy"],
        "key": features_data["key"],
        "loudness": features_data["loudness"],
        "mode": features_data["mode"],
        "speechiness": features_data["speechiness"],
        "acousticness": features_data["acousticness"],
        "instrumentalness": features_data["instrumentalness"],
        "liveness": features_data["liveness"],
        "valence": features_data["valence"],
        "tempo": features_data["tempo"],
    }


async def _fetch_features_and_track(track_id: str) -> tuple[dict, dict]:
    """Fetch audio features and track metadata concurrently."""
    features_task = asyncio.create_task(_spotify_get(f"/audio-features/{track_id}"))
    track_task = asyncio.create_task(_spotify_get(f"/tracks/{track_id}"))
    features_data, track_data = await asyncio.gather(features_task, track_task)
    return features_data, track_data
