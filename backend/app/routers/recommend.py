from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.music_catalog import MusicCatalog
from app.schemas.recommend import RecommendResponse, Track
from app.services.context_analyzer import ContextAnalyzer, get_context_analyzer
from app.services.recommendation import recommend_by_emotion
from app.services.stt import STTProvider, get_stt_provider

router = APIRouter(prefix="/recommend", tags=["recommend"])


def _to_track(catalog: MusicCatalog) -> Track:
    return Track(
        track_id=catalog.track_id,
        title=catalog.track_name,
        artist=catalog.artists,
        album=catalog.album_name,
        duration_sec=catalog.duration_ms // 1000,
        preview_url=catalog.preview_url,
    )


@router.post("", response_model=RecommendResponse)
async def recommend(
    audio: UploadFile,
    valence: float = Form(default=0.5),
    energy: float = Form(default=0.5),
    danceability: float = Form(default=0.5),
    acousticness: float = Form(default=0.5),
    instrumentalness: float = Form(default=0.5),
    db: Session = Depends(get_db),
    stt: STTProvider = Depends(get_stt_provider),
    analyzer: ContextAnalyzer = Depends(get_context_analyzer),
) -> RecommendResponse:
    emotion_vector = {
        "valence": valence,
        "energy": energy,
        "danceability": danceability,
        "acousticness": acousticness,
        "instrumentalness": instrumentalness,
    }

    transcript: str | None = None
    audio_bytes = await audio.read()
    if audio_bytes:
        transcript = await stt.transcribe(audio_bytes, audio.filename or "audio.wav")
        if transcript:
            emotion_vector = await analyzer.analyze(transcript)

    tracks = recommend_by_emotion(db, emotion_vector)
    return RecommendResponse(tracks=[_to_track(t) for t in tracks], transcript=transcript)
