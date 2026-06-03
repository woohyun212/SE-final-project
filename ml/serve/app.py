"""
EmotionClassifier 추론 서버
엔드포인트: POST /predict — 음성 파일 → 감정 벡터

실행:
    cd ml/
    uvicorn serve.app:app --host 0.0.0.0 --port 8001
"""

import io
from contextlib import asynccontextmanager

import soundfile as sf
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from serve.predictor import load_model, predict


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_model()  # 서버 시작 시 모델 미리 로드 (cold start 방지)
    yield


app = FastAPI(title="EmotionClassifier", version="0.1.0", lifespan=lifespan)


class EmotionVector(BaseModel):
    label: str
    valence: float
    arousal: float
    dominance: float
    confidence: float
    probabilities: dict[str, float]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=EmotionVector)
async def predict_emotion(audio: UploadFile = File(default=...)):
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="빈 파일")

    try:
        sf.info(io.BytesIO(audio_bytes))
    except Exception:
        raise HTTPException(status_code=400, detail="지원하지 않는 오디오 포맷입니다")

    try:
        result = predict(audio_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return result
