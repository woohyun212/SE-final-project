"""Unit tests for STTService and ContextAnalyzer (external calls are mocked)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.context_analyzer import ContextAnalyzer, _FEATURE_DEFAULTS
from app.services.stt import OpenAISTTProvider  # openai is now a module-level import


# ---------------------------------------------------------------------------
# STTService — OpenAI Whisper API backend
# ---------------------------------------------------------------------------

class TestOpenAISTTProvider:
    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self):
        mock_response = MagicMock()
        mock_response.text = "오늘 기분이 너무 좋아"

        with patch("app.services.stt.openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            provider = OpenAISTTProvider(api_key="test-key")
            result = await provider.transcribe(b"audio-bytes", "test.wav")

        assert result == "오늘 기분이 너무 좋아"

    @pytest.mark.asyncio
    async def test_transcribe_empty_bytes_returns_empty(self):
        provider = OpenAISTTProvider(api_key="test-key")
        result = await provider.transcribe(b"", "test.wav")
        assert result == ""

    @pytest.mark.asyncio
    async def test_transcribe_strips_whitespace(self):
        mock_response = MagicMock()
        mock_response.text = "  슬프고 지쳐있어  "

        with patch("app.services.stt.openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            provider = OpenAISTTProvider(api_key="test-key")
            result = await provider.transcribe(b"audio", "test.wav")

        assert result == "슬프고 지쳐있어"

    @pytest.mark.asyncio
    async def test_transcribe_default_language_is_korean(self):
        mock_response = MagicMock()
        mock_response.text = "안녕"

        with patch("app.services.stt.openai.AsyncOpenAI") as mock_cls:
            mock_client = AsyncMock()
            create_mock = AsyncMock(return_value=mock_response)
            mock_client.audio.transcriptions.create = create_mock
            mock_cls.return_value = mock_client

            provider = OpenAISTTProvider(api_key="test-key")
            await provider.transcribe(b"audio", "test.wav")

        call_kwargs = create_mock.call_args.kwargs
        assert call_kwargs.get("language") == "ko"


# ---------------------------------------------------------------------------
# ContextAnalyzer — google-genai SDK backend
# ---------------------------------------------------------------------------

def _mock_genai_response(content: str) -> MagicMock:
    response = MagicMock()
    response.text = content
    return response


def _patch_genai_client(response_text: str):
    """Returns a context manager that patches genai.Client and its async generate call."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=_mock_genai_response(response_text)
    )
    return patch("app.services.context_analyzer.genai.Client", return_value=mock_client)


class TestContextAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_returns_feature_vector(self):
        payload = json.dumps({
            "valence": 0.8,
            "energy": 0.7,
            "danceability": 0.6,
            "acousticness": 0.3,
            "instrumentalness": 0.1,
        })

        with _patch_genai_client(payload):
            analyzer = ContextAnalyzer(api_key="test-key")
            result = await analyzer.analyze("오늘 너무 신나고 기쁘다")

        assert result["valence"] == pytest.approx(0.8)
        assert result["energy"] == pytest.approx(0.7)
        assert set(result.keys()) == {"valence", "energy", "danceability", "acousticness", "instrumentalness"}

    @pytest.mark.asyncio
    async def test_analyze_empty_text_returns_defaults(self):
        analyzer = ContextAnalyzer(api_key="test-key")
        result = await analyzer.analyze("   ")
        assert result == _FEATURE_DEFAULTS

    @pytest.mark.asyncio
    async def test_analyze_clamps_out_of_range_values(self):
        payload = json.dumps({
            "valence": 1.5,
            "energy": -0.3,
            "danceability": 0.5,
            "acousticness": 0.5,
            "instrumentalness": 0.5,
        })

        with _patch_genai_client(payload):
            analyzer = ContextAnalyzer(api_key="test-key")
            result = await analyzer.analyze("극단적인 감정")

        assert result["valence"] == pytest.approx(1.0)
        assert result["energy"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_analyze_invalid_json_returns_defaults(self):
        with _patch_genai_client("not valid json {{"):
            analyzer = ContextAnalyzer(api_key="test-key")
            result = await analyzer.analyze("아무 말이나")

        assert result == _FEATURE_DEFAULTS

    @pytest.mark.asyncio
    async def test_analyze_missing_keys_use_defaults(self):
        payload = json.dumps({"valence": 0.9})

        with _patch_genai_client(payload):
            analyzer = ContextAnalyzer(api_key="test-key")
            result = await analyzer.analyze("슬프다")

        assert result["valence"] == pytest.approx(0.9)
        assert result["energy"] == pytest.approx(0.5)   # default
        assert result["danceability"] == pytest.approx(0.5)
