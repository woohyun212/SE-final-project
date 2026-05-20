"""
serve/predictor.py 단위 테스트
모델 파일 없이 실행 가능한 항목만 포함 (모델 의존 테스트는 별도 마킹)
"""

import io
import numpy as np
import pytest
import soundfile as sf

from train.dataset import VAD_MAP, EMOTION_LABELS, LABEL2ID, ID2LABEL


def make_dummy_wav(duration_sec: float = 1.0, sr: int = 16000) -> bytes:
    samples = np.zeros(int(duration_sec * sr), dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, samples, sr, format="WAV")
    return buf.getvalue()


def test_vad_map_keys_match_labels():
    assert set(VAD_MAP.keys()) == set(EMOTION_LABELS)


def test_vad_values_in_range():
    for label, (v, a, d) in VAD_MAP.items():
        assert -1.0 <= v <= 1.0, f"{label} valence out of range"
        assert -1.0 <= a <= 1.0, f"{label} arousal out of range"
        assert -1.0 <= d <= 1.0, f"{label} dominance out of range"


def test_label_id_roundtrip():
    for label in EMOTION_LABELS:
        assert ID2LABEL[LABEL2ID[label]] == label


def test_dummy_wav_readable():
    wav_bytes = make_dummy_wav()
    audio, sr = sf.read(io.BytesIO(wav_bytes))
    assert sr == 16000
    assert len(audio) > 0


@pytest.mark.skip(reason="모델 파일(model/best/) 필요 — 학습 후 실행")
def test_predict_returns_valid_vector():
    from serve.predictor import predict
    wav_bytes = make_dummy_wav()
    result = predict(wav_bytes)
    assert result["label"] in EMOTION_LABELS
    assert -1.0 <= result["valence"] <= 1.0
    assert -1.0 <= result["arousal"] <= 1.0
    assert -1.0 <= result["dominance"] <= 1.0
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-4
