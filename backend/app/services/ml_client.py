import logging
import os

import httpx

logger = logging.getLogger(__name__)


class VADResult:
    def __init__(self, valence: float, arousal: float, dominance: float):
        self.valence = valence
        self.arousal = arousal
        self.dominance = dominance


class MLClient:
    def __init__(self, base_url: str | None = None):
        self._base_url = (base_url or os.getenv("ML_SERVICE_URL", "http://localhost:8001")).rstrip("/")

    async def predict(self, audio_bytes: bytes) -> VADResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
            response = await client.post(f"{self._base_url}/predict", files=files)
            response.raise_for_status()
            body = response.json()

        return VADResult(
            valence=body["valence"],
            arousal=body["arousal"],
            dominance=body["dominance"],
        )


_client: MLClient | None = None


def get_ml_client() -> MLClient:
    global _client
    if _client is None:
        _client = MLClient()
        logger.info("MLClient: target=%s", _client._base_url)
    return _client
