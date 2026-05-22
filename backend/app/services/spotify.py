import asyncio
import os
import time
import logging
from typing import TypedDict

import httpx
from pydantic import BaseModel

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


# ---------------------------------------------------------------------------
# Internal Pydantic models — validate Spotify API response shapes (#9)
# ---------------------------------------------------------------------------

class _SpotifyArtist(BaseModel):
    name: str


class _SpotifyAlbum(BaseModel):
    name: str


class _SpotifyTrackItem(BaseModel):
    id: str
    name: str
    artists: list[_SpotifyArtist]
    album: _SpotifyAlbum
    duration_ms: int
    preview_url: str | None = None


class _SpotifyTracksPage(BaseModel):
    items: list[_SpotifyTrackItem]
    total: int


class _SpotifySearchResponse(BaseModel):
    tracks: _SpotifyTracksPage


class _SpotifyAudioFeatures(BaseModel):
    danceability: float
    energy: float
    key: int
    loudness: float
    mode: int
    speechiness: float
    acousticness: float
    instrumentalness: float
    liveness: float
    valence: float
    tempo: float
    duration_ms: int


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SpotifyCredentialsError(RuntimeError):
    """Raised when Spotify API credentials are missing from environment."""


class SpotifyNotFoundError(Exception):
    """Raised when Spotify returns 404 for a requested resource."""


class RateLimitError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Spotify rate limit hit — retry after {retry_after}s")


# ---------------------------------------------------------------------------
# HTTP client management
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Token management
# ---------------------------------------------------------------------------

async def _get_access_token() -> str:
    """Client Credentials Flow — token is cached until 60 s before expiry."""
    # 자격증명을 매 호출 시 검증해 캐시 유효 중에 env가 사라져도 즉시 감지한다 (#5)
    client_id, client_secret = _get_credentials()
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    async with _token_lock:
        now = time.time()  # re-check after acquiring lock to avoid duplicate refresh
        if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
            return _token_cache["access_token"]

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


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def _parse_track(item: dict) -> dict:
    # Pydantic으로 파싱해 누락 키로 인한 KeyError → 500 을 방지한다 (#9)
    track = _SpotifyTrackItem.model_validate(item)
    return {
        "track_id": track.id,
        "name": track.name,
        "artists": [a.name for a in track.artists],
        "album": track.album.name,
        "duration_ms": track.duration_ms,
        "preview_url": track.preview_url,
    }


async def search_tracks(query: str, limit: int = 10, offset: int = 0) -> dict:
    """Search Spotify tracks. Returns list of track summaries + total count."""
    raw = await _spotify_get(
        "/search",
        params={"q": query, "type": "track", "limit": limit, "offset": offset},
    )
    # Pydantic으로 응답 구조를 검증해 예상치 못한 형태에도 안전하게 처리 (#9)
    parsed = _SpotifySearchResponse.model_validate(raw)
    return {
        "tracks": [_parse_track(t.model_dump(mode="python")) for t in parsed.tracks.items],
        "total": parsed.tracks.total,
    }


async def get_audio_features(track_id: str, include_metadata: bool = True) -> dict:
    """Fetch audio features for a single track.

    include_metadata=True(기본값)이면 /tracks/{id} 를 병렬 호출해 이름·아티스트·앨범을 병합한다.
    False이면 /audio-features 단독 호출로 Spotify 쿼터를 절반으로 줄인다 (#8).

    NOTE: audio-features is deprecated for Spotify apps created after 2024-11-27.
    Verify the app predates this cutoff and holds a quota extension before deploying.
    """
    features_raw = None
    track_raw = None

    if include_metadata:
        features_raw, track_raw = await _fetch_features_and_track(track_id)
    else:
        features_raw = await _spotify_get(f"/audio-features/{track_id}")

    features = _SpotifyAudioFeatures.model_validate(features_raw)

    result: dict = {
        "track_id": track_id,
        "duration_ms": features.duration_ms,
        "danceability": features.danceability,
        "energy": features.energy,
        "key": features.key,
        "loudness": features.loudness,
        "mode": features.mode,
        "speechiness": features.speechiness,
        "acousticness": features.acousticness,
        "instrumentalness": features.instrumentalness,
        "liveness": features.liveness,
        "valence": features.valence,
        "tempo": features.tempo,
    }

    if include_metadata and track_raw is not None:
        track = _SpotifyTrackItem.model_validate(track_raw)
        result["name"] = track.name
        result["artists"] = [a.name for a in track.artists]
        result["album"] = track.album.name
    else:
        result["name"] = None
        result["artists"] = None
        result["album"] = None

    return result


async def _fetch_features_and_track(track_id: str) -> tuple[dict, dict]:
    """Fetch audio features and track metadata concurrently."""
    features_task = asyncio.create_task(_spotify_get(f"/audio-features/{track_id}"))
    track_task = asyncio.create_task(_spotify_get(f"/tracks/{track_id}"))
    features_data, track_data = await asyncio.gather(features_task, track_task)
    return features_data, track_data
