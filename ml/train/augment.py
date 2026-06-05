import numpy as np

from train.dataset import SAMPLING_RATE


def augment(audio: np.ndarray, sr: int = SAMPLING_RATE) -> np.ndarray:
    """노이즈 추가 + 피치 변환 + 속도 변환 중 무작위 조합 적용."""
    if np.random.random() < 0.5:
        audio = _add_noise(audio)
    if np.random.random() < 0.5:
        audio = _pitch_shift(audio, sr)
    if np.random.random() < 0.5:
        audio = _time_stretch(audio)
    return audio.astype(np.float32)


def _add_noise(audio: np.ndarray, snr_db_range: tuple = (5, 20)) -> np.ndarray:
    snr_db = np.random.uniform(*snr_db_range)
    signal_rms = np.sqrt(np.mean(audio ** 2)) + 1e-9
    noise_rms = signal_rms / (10 ** (snr_db / 20))
    noise = np.random.normal(0, noise_rms, len(audio))
    return audio + noise


def _pitch_shift(audio: np.ndarray, sr: int, semitone_range: float = 2.0) -> np.ndarray:
    import librosa
    n_steps = np.random.uniform(-semitone_range, semitone_range)
    return librosa.effects.pitch_shift(audio, sr=sr, n_steps=n_steps)


def _time_stretch(audio: np.ndarray, rate_range: tuple = (0.9, 1.1)) -> np.ndarray:
    import librosa
    rate = np.random.uniform(*rate_range)
    return librosa.effects.time_stretch(audio, rate=rate)
