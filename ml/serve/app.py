"""
EmotionClassifier 추론 서버
엔드포인트: POST /ml/predict — 음성 파일 → 감정 벡터

실행:
    cd ml/
    uvicorn serve.app:app --host 0.0.0.0 --port 8001
"""

import soundfile as sf

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


@app.post("/predict", response_model=EmotionVector)
async def predict_emotion(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="빈 파일")

    # Content-Type 대신 실제 바이트로 포맷 검증
    # (클라이언트가 application/octet-stream으로 올리는 경우 대응)
    try:
        import io
        sf.info(io.BytesIO(audio_bytes))
    except Exception:
        raise HTTPException(status_code=400, detail="지원하지 않는 오디오 포맷입니다")

    try:
        result = predict(audio_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result
