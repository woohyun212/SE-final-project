import logging
import os

import httpx

logger = logging.getLogger(__name__)

class MLResult:
    def __init__(self, track_indices: list[int], emotions: dict[str, float] | None = None):
        self.track_indices = track_indices
        self.emotions = emotions


class MLClient:
    def __init__(self, base_url: str | None = None):
        self._base_url = (base_url or os.getenv("ML_SERVICE_URL", "http://localhost:8081")).rstrip("/")

    async def predict(self, audio_bytes: bytes, transcript: str) -> MLResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
            data = {"transcript": transcript}
            response = await client.post(f"{self._base_url}/predict", files=files, data=data)
            response.raise_for_status()
            body = response.json()

        return MLResult(
            track_indices=body["track_indices"],
            emotions=body.get("emotions"),
        )


_client: MLClient | None = None


def get_ml_client() -> MLClient:
    global _client
    if _client is None:
        _client = MLClient()
        logger.info("MLClient: target=%s", _client._base_url)
    return _client
