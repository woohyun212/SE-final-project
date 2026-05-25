import asyncio
import logging
import os
from typing import Protocol, runtime_checkable

import openai

logger = logging.getLogger(__name__)


@runtime_checkable
class STTProvider(Protocol):
    async def transcribe(self, audio_bytes: bytes, filename: str) -> str: ...


class OpenAISTTProvider:
    """Whisper API backend — cloud, pay-per-use."""

    def __init__(self, api_key: str | None = None, language: str = "ko"):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._language = language

    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        if not audio_bytes:
            return ""

        client = openai.AsyncOpenAI(api_key=self._api_key)
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_bytes),
            language=self._language,
        )
        transcript = response.text.strip()
        logger.info("STT(api) transcript (len=%d): %.80s", len(transcript), transcript)
        return transcript


class LocalWhisperProvider:
    """Whisper Small local backend — no API cost, runs on CPU/GPU."""

    def __init__(self, model_size: str = "small", language: str = "ko"):
        self._model_size = model_size
        self._language = language
        self._model = None  # lazy-load on first use

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
            logger.info("LocalWhisperProvider: loaded model '%s'", self._model_size)

    def _run_transcribe(self, audio_bytes: bytes) -> str:
        import io

        self._load_model()
        segments, _ = self._model.transcribe(
            io.BytesIO(audio_bytes),
            language=self._language,
            beam_size=5,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.info("STT(local) transcript (len=%d): %.80s", len(text), text)
        return text

    async def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        if not audio_bytes:
            return ""
        # faster-whisper inference is CPU-bound — run in thread pool to avoid blocking
        return await asyncio.to_thread(self._run_transcribe, audio_bytes)


_provider: STTProvider | None = None


def get_stt_provider() -> STTProvider:
    """Factory: picks provider from STT_PROVIDER env var ('api' | 'local', default 'api')."""
    global _provider
    if _provider is None:
        backend = os.getenv("STT_PROVIDER", "api").lower()
        if backend == "local":
            model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
            _provider = LocalWhisperProvider(model_size=model_size)
            logger.info("STTService: using local Whisper (%s)", model_size)
        else:
            _provider = OpenAISTTProvider()
            logger.info("STTService: using Whisper API")
    return _provider
