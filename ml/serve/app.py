"""
EmotionClassifier 추론 서버
엔드포인트: POST /ml/predict — 음성 파일 → 감정 벡터

실행:
    cd ml/
    uvicorn serve.app:app --host 0.0.0.0 --port 8001
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel

from serve.predictor import predict

app = FastAPI(title="EmotionClassifier", version="0.1.0")


class EmotionVector(BaseModel):
    label: str
    valence: float
    arousal: float
    dominance: float
    probabilities: dict[str, float]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ml/predict", response_model=EmotionVector)
async def predict_emotion(audio: UploadFile = File(...)):
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="audio/* 형식의 파일만 허용")

    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="빈 파일")

    try:
        result = predict(audio_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result
