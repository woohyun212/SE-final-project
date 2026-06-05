import logging
import os

import httpx

logger = logging.getLogger(__name__)

# VAD [-1, 1] 공간 — (valence, arousal, dominance)
_KEYWORD_VAD: dict[str, tuple[float, float, float]] = {
    "happy": (0.6, 0.4, 0.2), "기쁘": (0.6, 0.4, 0.2), "행복": (0.6, 0.3, 0.2),
    "excited": (0.4, 0.8, 0.3), "신나": (0.4, 0.8, 0.3), "좋아": (0.4, 0.2, 0.2),
    "calm": (0.4, -0.6, 0.0), "평온": (0.4, -0.6, 0.0), "차분": (0.4, -0.6, 0.0),
    "편안": (0.4, -0.6, 0.0), "relaxed": (0.4, -0.6, 0.0),
    "sad": (-0.6, -0.4, -0.4), "슬프": (-0.6, -0.4, -0.4),
    "depressed": (-0.8, -0.6, -0.6), "우울": (-0.8, -0.6, -0.6),
    "tired": (-0.4, -0.6, -0.4), "피곤": (-0.4, -0.6, -0.4), "지치": (-0.4, -0.6, -0.4),
    "외롭": (-0.6, -0.6, -0.4), "lonely": (-0.6, -0.6, -0.4),
    "angry": (-0.6, 0.6, 0.4), "화나": (-0.6, 0.6, 0.4),
    "짜증": (-0.6, 0.4, 0.0), "frustrated": (-0.6, 0.4, 0.0),
    "스트레스": (-0.6, 0.4, -0.2), "stressed": (-0.6, 0.4, -0.2),
    "불안": (-0.4, 0.4, -0.4), "anxious": (-0.4, 0.4, -0.4),
    "긴장": (-0.2, 0.4, -0.2), "nervous": (-0.2, 0.4, -0.2),
}


class VADResult:
    def __init__(self, valence: float, arousal: float, dominance: float):
        self.valence = valence
        self.arousal = arousal
        self.dominance = dominance


def vad_from_text(transcript: str) -> VADResult:
    """transcript 감정 키워드 → VAD 추정. 매칭 없으면 중립 (0.0, 0.0, 0.0) 반환.

    부분 문자열 매칭(kw in text) 사용 — 오매칭 가능하나 폴백 휴리스틱 수준으로 허용.
    복수 키워드 매칭 시 VAD를 단순 평균함 — 동의어 중복 매칭 시 강도가 희석될 수 있음.
    """
    if not transcript:
        return VADResult(0.0, 0.0, 0.0)
    text = transcript.lower()
    matches = [vad for kw, vad in _KEYWORD_VAD.items() if kw in text]
    if not matches:
        return VADResult(0.0, 0.0, 0.0)
    n = len(matches)
    return VADResult(
        valence=sum(v for v, _, _ in matches) / n,
        arousal=sum(a for _, a, _ in matches) / n,
        dominance=sum(d for _, _, d in matches) / n,
    )


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
