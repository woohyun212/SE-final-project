import io
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForSequenceClassification

from serve.audio_preprocess import preprocess
from train.dataset import ID2LABEL, MAX_DURATION_SEC, SAMPLING_RATE, VAD_MAP

MODEL_DIR = str(Path(__file__).parent.parent / "model" / "best")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CONFIDENCE_THRESHOLD = 0.4

_model: Wav2Vec2ForSequenceClassification | None = None
_extractor: Wav2Vec2FeatureExtractor | None = None


def load_model() -> None:
    global _model, _extractor
    if not Path(MODEL_DIR).exists():
        raise RuntimeError(f"모델 없음: {MODEL_DIR} — 학습 먼저 실행하세요 (make train)")
    _extractor = Wav2Vec2FeatureExtractor.from_pretrained(MODEL_DIR)
    _model = Wav2Vec2ForSequenceClassification.from_pretrained(MODEL_DIR).to(DEVICE)
    _model.eval()
    print(f"모델 로드 완료 (device={DEVICE})")


def predict(audio_bytes: bytes) -> dict:
    """음성 바이트 → 감정 벡터 (valence, arousal, dominance) + 레이블 + 확률
    confidence는 top 예측 클래스의 softmax 확률. CONFIDENCE_THRESHOLD 미만이면 neutral fallback.
    """
    if _model is None or _extractor is None:
        raise RuntimeError("모델이 로드되지 않았습니다. 서버 재시작이 필요합니다.")

    audio, sr = sf.read(io.BytesIO(audio_bytes))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLING_RATE:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLING_RATE)

    audio = audio[: MAX_DURATION_SEC * SAMPLING_RATE].astype(np.float32)
    audio = preprocess(audio, SAMPLING_RATE)

    inputs = _extractor(audio, sampling_rate=SAMPLING_RATE, return_tensors="pt", padding=True)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    with torch.no_grad():
        logits = _model(**inputs).logits

    probs = torch.softmax(logits, dim=-1).squeeze().tolist()
    pred_id = int(torch.argmax(logits))
    confidence = round(max(probs), 4)

    pred_label = "neutral" if confidence < CONFIDENCE_THRESHOLD else ID2LABEL[pred_id]
    valence, arousal, dominance = VAD_MAP[pred_label]

    return {
        "label": pred_label,
        "valence": valence,
        "arousal": arousal,
        "dominance": dominance,
        "confidence": confidence,
        "probabilities": {ID2LABEL[i]: round(p, 4) for i, p in enumerate(probs)},
    }
