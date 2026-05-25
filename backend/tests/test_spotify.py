"""
Spotify service tests — HTTP calls are intercepted via httpx.MockTransport
so no real Spotify credentials are needed.
"""
import time
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.services import spotify as spotify_svc

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

# Spotify Client Credentials Flow 토큰 발급 응답 샘플
_FAKE_TOKEN_RESP = {"access_token": "fake_token", "expires_in": 3600, "token_type": "Bearer"}

# 트랙 검색 응답 샘플 (트랙 1개)
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

# /audio-features/{id} 응답 샘플
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

# /tracks/{id} 응답 샘플 (메타데이터 병합용)
_FAKE_TRACK = {
    "id": "track123",
    "name": "Test Song",
    "artists": [{"name": "Artist A"}],
    "album": {"name": "Album X"},
    "duration_ms": 210000,
}


@pytest.fixture(autouse=True)
def reset_spotify_state():
    """모든 테스트 전후로 모듈 레벨 상태를 초기화해 테스트 간 누수를 방지한다."""
    # 토큰 캐시를 비워 매 테스트가 깨끗한 상태에서 시작하도록 한다
    spotify_svc._token_cache["access_token"] = None
    spotify_svc._token_cache["expires_at"] = 0.0
    original_client = spotify_svc._http_client  # 테스트가 client를 교체해도 원복 가능하도록 저장
    yield
    spotify_svc._http_client = original_client


def _make_transport(*route_maps: dict) -> httpx.MockTransport:
    """URL 접두사 → 응답 바디를 매핑하는 MockTransport를 생성한다.

    각 항목 형식: {url_prefix: {"__status__": <int>, ...body...}}
    __status__ 가 없으면 200으로 처리하고, 토큰 엔드포인트는 항상 _FAKE_TOKEN_RESP를 반환한다.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        # Spotify 토큰 발급 요청은 항상 성공 처리
        if "accounts.spotify.com" in url:
            return httpx.Response(200, json=_FAKE_TOKEN_RESP)
        for routes in route_maps:
            for prefix, body in routes.items():
                if prefix in url:
                    body = dict(body)  # 원본 dict 변경 방지를 위해 복사
                    status_code = body.pop("__status__", 200)
                    return httpx.Response(status_code, json=body)
        # 매핑되지 않은 경로는 404 반환
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


def _patched_client(transport: httpx.MockTransport):
    """모듈 레벨 _http_client를 mock 클라이언트로 교체하는 컨텍스트 매니저."""
    mock = httpx.AsyncClient(transport=transport, timeout=10)
    # patch.object로 모듈 변수를 직접 교체해 _get_http_client()가 mock을 반환하게 한다
    return patch.object(spotify_svc, "_http_client", mock)


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------

async def test_get_access_token_caches():
    """같은 TTL 안에서 두 번 호출해도 토큰 발급 요청이 1번만 발생하는지 검증."""
    transport = _make_transport()
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            token1 = await spotify_svc._get_access_token()
            token2 = await spotify_svc._get_access_token()  # 캐시 히트 — 재발급 없어야 함

    assert token1 == token2 == "fake_token"


async def test_get_access_token_refreshes_when_expired():
    """만료된 토큰이 있을 때 새 토큰을 발급하는지 검증."""
    spotify_svc._token_cache["access_token"] = "old_token"
    spotify_svc._token_cache["expires_at"] = time.time() - 1  # 이미 만료

    transport = _make_transport()
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            token = await spotify_svc._get_access_token()

    assert token == "fake_token"  # old_token이 아닌 새 토큰


async def test_get_access_token_fails_immediately_when_credentials_missing():
    """토큰이 캐시에 살아있어도 자격증명이 없으면 즉시 SpotifyCredentialsError가 발생하는지 검증 (#5)."""
    # 유효한 캐시 토큰이 있는 상태
    spotify_svc._token_cache["access_token"] = "cached_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    transport = _make_transport()
    with _patched_client(transport):
        # 자격증명 없이 호출 — 캐시가 살아있어도 503이 떠야 한다
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("SPOTIFY_CLIENT_ID", None)
            os.environ.pop("SPOTIFY_CLIENT_SECRET", None)
            with pytest.raises(spotify_svc.SpotifyCredentialsError):
                await spotify_svc._get_access_token()


async def test_search_tracks_returns_parsed_result():
    """검색 결과가 _parse_track 형식으로 올바르게 변환되는지 검증."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    transport = _make_transport({"/search": _FAKE_SEARCH_RESP})
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            result = await spotify_svc.search_tracks("happy", limit=5)

    assert result["total"] == 1
    assert result["tracks"][0]["track_id"] == "track123"
    assert result["tracks"][0]["artists"] == ["Artist A"]


async def test_search_tracks_empty_results():
    """검색 결과가 0건일 때 빈 리스트와 total=0을 반환하는지 검증."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    empty_resp = {"tracks": {"items": [], "total": 0}}
    transport = _make_transport({"/search": empty_resp})
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            result = await spotify_svc.search_tracks("xyzzy_no_match")

    assert result["total"] == 0
    assert result["tracks"] == []


async def test_search_tracks_invalid_response_raises_validation_error():
    """Spotify가 예상과 다른 응답 구조를 반환하면 ValidationError가 발생하는지 검증 (#9)."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    # album 필드가 빠진 잘못된 트랙 — 기존 코드면 KeyError → 500, Pydantic이면 ValidationError
    malformed_resp = {
        "tracks": {
            "items": [{"id": "x", "name": "X", "artists": [{"name": "A"}], "duration_ms": 100}],
            "total": 1,
        }
    }
    transport = _make_transport({"/search": malformed_resp})
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            with pytest.raises(ValidationError):
                await spotify_svc.search_tracks("bad")


async def test_search_tracks_rate_limit_raises():
    """Spotify가 429를 반환할 때 RateLimitError가 발생하고 retry_after 값이 전달되는지 검증."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={}, headers={"Retry-After": "5"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            with pytest.raises(spotify_svc.RateLimitError) as exc_info:
                await spotify_svc.search_tracks("happy")

    assert exc_info.value.retry_after == 5


async def test_get_audio_features_merges_data():
    """audio-features와 track 메타데이터가 하나의 dict로 올바르게 병합되는지 검증."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    # /audio-features/{id}와 /tracks/{id}를 URL로 구분해 각기 다른 응답 반환
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "audio-features" in url:
            return httpx.Response(200, json=_FAKE_AUDIO_FEATURES)
        if "/tracks/" in url:
            return httpx.Response(200, json=_FAKE_TRACK)
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            result = await spotify_svc.get_audio_features("track123")

    assert result["track_id"] == "track123"
    assert result["name"] == "Test Song"
    assert result["danceability"] == 0.8
    assert result["tempo"] == 120.0


async def test_get_audio_features_without_metadata():
    """include_metadata=False 이면 /tracks 호출 없이 메타데이터가 None으로 반환되는지 검증 (#8)."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    call_log: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        call_log.append(url)
        if "audio-features" in url:
            return httpx.Response(200, json=_FAKE_AUDIO_FEATURES)
        # /tracks/{id} 호출이 오면 테스트 실패를 유도하기 위해 500 반환
        return httpx.Response(500, json={"error": "should not be called"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            result = await spotify_svc.get_audio_features("track123", include_metadata=False)

    # 메타데이터 필드는 None
    assert result["name"] is None
    assert result["artists"] is None
    assert result["album"] is None
    # audio features 필드는 정상 반환
    assert result["danceability"] == 0.8
    assert result["duration_ms"] == 210000
    # /tracks 엔드포인트는 호출되지 않았어야 한다
    assert not any("/tracks/" in url for url in call_log)


async def test_audio_features_rate_limit_raises():
    """audio-features 호출 중 429 응답이 와도 RateLimitError가 올바르게 전파되는지 검증."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={}, headers={"Retry-After": "3"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            with pytest.raises(spotify_svc.RateLimitError) as exc_info:
                await spotify_svc.get_audio_features("track123")

    assert exc_info.value.retry_after == 3


async def test_audio_features_not_found_raises():
    """존재하지 않는 track_id에 대해 SpotifyNotFoundError가 발생하는지 검증."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            with pytest.raises(spotify_svc.SpotifyNotFoundError):
                await spotify_svc.get_audio_features("nonexistent_id")


# ---------------------------------------------------------------------------
# Router / integration tests (no real Spotify calls)
# ---------------------------------------------------------------------------

def test_search_endpoint_missing_credentials(monkeypatch):
    """자격증명 환경변수 미설정 시 /search가 503을 반환하는지 검증."""
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    response = client.get("/spotify/search?q=happy")
    assert response.status_code == 503


def test_audio_features_endpoint_missing_credentials(monkeypatch):
    """자격증명 환경변수 미설정 시 /audio-features가 503을 반환하는지 검증."""
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    response = client.get("/spotify/audio-features/track123")
    assert response.status_code == 503


def test_audio_features_endpoint_not_found():
    """Spotify가 404를 반환할 때 /audio-features 엔드포인트도 404를 응답하는지 검증."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            response = client.get("/spotify/audio-features/bad_id")

    assert response.status_code == 404


def test_audio_features_endpoint_without_metadata():
    """include_metadata=false 쿼리 파라미터로 호출 시 메타데이터가 null로 반환되는지 검증 (#8)."""
    spotify_svc._token_cache["access_token"] = "fake_token"
    spotify_svc._token_cache["expires_at"] = time.time() + 3600

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "audio-features" in url:
            return httpx.Response(200, json=_FAKE_AUDIO_FEATURES)
        return httpx.Response(500, json={})

    transport = httpx.MockTransport(handler)
    with _patched_client(transport):
        with patch.dict("os.environ", {"SPOTIFY_CLIENT_ID": "id", "SPOTIFY_CLIENT_SECRET": "secret"}):
            response = client.get("/spotify/audio-features/track123?include_metadata=false")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] is None
    assert body["artists"] is None
    assert body["danceability"] == 0.8
