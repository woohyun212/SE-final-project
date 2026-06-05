import os
import warnings
from dataclasses import dataclass

import numpy as np
import soundfile as sf
from transformers import Wav2Vec2FeatureExtractor

# seungjunlim/emotion-dataset-audio 의 감정 레이블
# 다운로드 후 실제 레이블 확인하여 수정 필요
EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
LABEL2ID = {label: i for i, label in enumerate(EMOTION_LABELS)}
ID2LABEL = {i: label for i, label in enumerate(EMOTION_LABELS)}

# 감정 레이블 → VAD (Valence, Arousal, Dominance) 매핑
# Russell's circumplex model 기반 근사값
VAD_MAP: dict[str, tuple[float, float, float]] = {
    "angry":    (-0.6,  0.7,  0.7),
    "disgust":  (-0.5,  0.3,  0.4),
    "fear":     (-0.7,  0.6, -0.5),
    "happy":    ( 0.8,  0.6,  0.5),
    "neutral":  ( 0.0,  0.0,  0.0),
    "sad":      (-0.7, -0.4, -0.5),
    "surprise": ( 0.2,  0.7, -0.3),
}

SAMPLING_RATE = 16_000
MAX_DURATION_SEC = 10


@dataclass
class EmotionSample:
    path: str
    label: str
    label_id: int


def load_audio(path: str) -> np.ndarray:
    audio, sr = sf.read(path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLING_RATE:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLING_RATE)
    max_samples = MAX_DURATION_SEC * SAMPLING_RATE
    return audio[:max_samples].astype(np.float32)


def scan_dataset(data_dir: str) -> list[EmotionSample]:
    """data/raw/ 아래 <label>/<file>.wav 구조를 가정."""
    samples = []
    for label in EMOTION_LABELS:
        label_dir = os.path.join(data_dir, label)
        if not os.path.isdir(label_dir):
            warnings.warn(f"label dir not found: {label_dir}")
            continue
        for fname in os.listdir(label_dir):
            if fname.lower().endswith((".wav", ".mp3", ".flac")):
                samples.append(EmotionSample(
                    path=os.path.join(label_dir, fname),
                    label=label,
                    label_id=LABEL2ID[label],
                ))
    return samples


def preprocess_batch(samples: list[EmotionSample], extractor: Wav2Vec2FeatureExtractor) -> dict:
    waveforms = [load_audio(s.path) for s in samples]
    inputs = extractor(
        waveforms,
        sampling_rate=SAMPLING_RATE,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=MAX_DURATION_SEC * SAMPLING_RATE,
        return_attention_mask=True,
    )
    import torch
    inputs["labels"] = torch.tensor([s.label_id for s in samples], dtype=torch.long)
    return inputs
