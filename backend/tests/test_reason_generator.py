"""
ReasonGenerator 테스트

- mock 기반 파싱/분배 테스트: API 키 없이 동작 (결정적 커버리지)
- 트랙 수가 _LLM_REASON_LIMIT를 넘을 때 상위 N개만 LLM에 보내고 나머지는
  규칙 기반으로 채우는 동작 검증 (#177 — Gemini 응답 지연/타임아웃 완화)
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.reason_generator as reason_generator_module
from app.models.music_catalog import MusicCatalog
from app.services.reason_generator import ReasonGenerator, _rule_based_reason

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_generator(monkeypatch):
    monkeypatch.setattr(reason_generator_module, "_LLM_REASON_LIMIT", 2)
    with patch("app.services.reason_generator.genai.Client"):
        yield ReasonGenerator(api_key="fake-key")


def _resp(text: str) -> MagicMock:
    r = MagicMock()
    r.text = text
    return r


def _make_track(track_id: str, **kwargs) -> MusicCatalog:
    defaults = {
        "track_id": track_id,
        "track_name": f"Track {track_id}",
        "artists": "Test Artist",
        "album_name": "Test Album",
        "track_genre": "pop",
        "duration_ms": 200_000,
        "speechiness": 0.05,
        "liveness": 0.1,
        "tempo": 120.0,
        "loudness": -8.0,
        "key": 0,
        "mode": 1,
        "time_signature": 4,
        "danceability": 0.5,
        "energy": 0.5,
        "valence": 0.5,
        "acousticness": 0.2,
        "instrumentalness": 0.1,
    }
    defaults.update(kwargs)
    return MusicCatalog(**defaults)


# ---------------------------------------------------------------------------
# 상위 N개만 LLM에 전달, 나머지는 규칙 기반 분배
# ---------------------------------------------------------------------------

async def test_generate_sends_only_top_n_tracks_to_llm(mock_generator):
    tracks = [_make_track(f"t{i}") for i in range(4)]  # limit=2 → t0,t1 LLM / t2,t3 rule-based
    mock_call = AsyncMock(
        return_value=_resp(json.dumps({"t0": "llm reason 0", "t1": "llm reason 1"}))
    )
    mock_generator._client.aio.models.generate_content = mock_call

    reasons, fallback = await mock_generator.generate(tracks, 0.5, 0.5, 0.5)

    assert fallback is False
    assert reasons["t0"] == "llm reason 0"
    assert reasons["t1"] == "llm reason 1"
    # 나머지는 규칙 기반 — fallback 표시 없이 채워짐
    assert reasons["t2"] == _rule_based_reason(tracks[2])
    assert reasons["t3"] == _rule_based_reason(tracks[3])

    # 프롬프트에 전달된 트랙은 상위 2개뿐이어야 한다 (출력 토큰 절감)
    prompt = mock_call.call_args.kwargs["contents"]
    assert "t0" in prompt and "t1" in prompt
    assert "t2" not in prompt and "t3" not in prompt


async def test_generate_sends_all_tracks_when_within_limit(mock_generator):
    tracks = [_make_track("t0"), _make_track("t1")]
    mock_call = AsyncMock(
        return_value=_resp(json.dumps({"t0": "llm reason 0", "t1": "llm reason 1"}))
    )
    mock_generator._client.aio.models.generate_content = mock_call

    reasons, fallback = await mock_generator.generate(tracks, 0.5, 0.5, 0.5)

    assert fallback is False
    assert reasons == {"t0": "llm reason 0", "t1": "llm reason 1"}


async def test_generate_fills_missing_llm_reason_with_rule_based(mock_generator):
    tracks = [_make_track("t0"), _make_track("t1")]
    # LLM이 t1에 대한 reason을 빠뜨린 경우
    mock_generator._client.aio.models.generate_content = AsyncMock(
        return_value=_resp(json.dumps({"t0": "llm reason 0"}))
    )

    reasons, fallback = await mock_generator.generate(tracks, 0.5, 0.5, 0.5)

    assert fallback is False
    assert reasons["t0"] == "llm reason 0"
    assert reasons["t1"] == _rule_based_reason(tracks[1])


# ---------------------------------------------------------------------------
# 실패/타임아웃 — 전체 트랙에 대해 규칙 기반 폴백 (fallback=True)
# ---------------------------------------------------------------------------

async def test_generate_timeout_falls_back_for_all_tracks(mock_generator):
    tracks = [_make_track(f"t{i}") for i in range(3)]
    mock_generator._client.aio.models.generate_content = AsyncMock(
        side_effect=asyncio.TimeoutError
    )

    reasons, fallback = await mock_generator.generate(tracks, 0.5, 0.5, 0.5)

    assert fallback is True
    assert reasons == {t.track_id: _rule_based_reason(t) for t in tracks}


async def test_generate_malformed_response_falls_back_for_all_tracks(mock_generator):
    tracks = [_make_track(f"t{i}") for i in range(3)]
    mock_generator._client.aio.models.generate_content = AsyncMock(
        return_value=_resp("not valid json at all")
    )

    reasons, fallback = await mock_generator.generate(tracks, 0.5, 0.5, 0.5)

    assert fallback is True
    assert reasons == {t.track_id: _rule_based_reason(t) for t in tracks}


async def test_generate_empty_tracks_returns_empty_without_api_call(mock_generator):
    mock_call = AsyncMock()
    mock_generator._client.aio.models.generate_content = mock_call

    reasons, fallback = await mock_generator.generate([], 0.5, 0.5, 0.5)

    assert reasons == {}
    assert fallback is False
    mock_call.assert_not_called()
