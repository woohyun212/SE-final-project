import numpy as np


def preprocess(audio: np.ndarray, sr: int) -> np.ndarray:
    """노이즈 제거 → 무음 trim → RMS 정규화 순서로 전처리."""
    audio = _reduce_noise(audio, sr)
    audio = _trim_silence(audio, sr)
    audio = _normalize_rms(audio)
    return audio


def _reduce_noise(audio: np.ndarray, sr: int) -> np.ndarray:
    try:
        import noisereduce as nr
        return nr.reduce_noise(y=audio, sr=sr, stationary=False).astype(np.float32)
    except Exception:
        return audio


def _trim_silence(audio: np.ndarray, sr: int, top_db: int = 30) -> np.ndarray:
    import librosa
    trimmed, _ = librosa.effects.trim(audio, top_db=top_db)
    # 무음만 있는 극단적 경우 대비
    return trimmed if len(trimmed) > sr * 0.1 else audio


def _normalize_rms(audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
    rms = np.sqrt(np.mean(audio ** 2))
    if rms < 1e-6:
        return audio
    return (audio * (target_rms / rms)).astype(np.float32)
