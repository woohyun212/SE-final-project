import io
from functools import lru_cache

import numpy as np
import soundfile as sf
import torch
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

from train.dataset import ID2LABEL, VAD_MAP, SAMPLING_RATE, MAX_DURATION_SEC

MODEL_DIR = "model/best"


@lru_cache(maxsize=1)
def _load_model() -> tuple[Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor]:
    extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_DIR)
    model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()
    return model, extractor


def predict(audio_bytes: bytes) -> dict:
    """음성 바이트 → 감정 벡터 (valence, arousal, dominance) + 레이블 + 확률"""
    audio, sr = sf.read(io.BytesIO(audio_bytes))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLING_RATE:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLING_RATE)

    audio = audio[: MAX_DURATION_SEC * SAMPLING_RATE].astype(np.float32)

    model, extractor = _load_model()
    inputs = extractor(audio, sampling_rate=SAMPLING_RATE, return_tensors="pt", padding=True)

    with torch.no_grad():
        logits = model(**inputs).logits

    probs = torch.softmax(logits, dim=-1).squeeze().tolist()
    pred_id = int(torch.argmax(logits))
    pred_label = ID2LABEL[pred_id]
    valence, arousal, dominance = VAD_MAP[pred_label]

    return {
        "label": pred_label,
        "valence": valence,
        "arousal": arousal,
        "dominance": dominance,
        "probabilities": {ID2LABEL[i]: round(p, 4) for i, p in enumerate(probs)},
    }
