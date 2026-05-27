from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.music_catalog import MusicCatalog
from app.schemas.recommend import RecommendResponse, Track
from app.services.ml_client import MLClient, get_ml_client
from app.services.recommendation import get_tracks_by_indices
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
    db: Session = Depends(get_db),
    stt: STTProvider = Depends(get_stt_provider),
    ml: MLClient = Depends(get_ml_client),
) -> RecommendResponse:
    audio_bytes = await audio.read()

    transcript: str | None = None
    if audio_bytes:
        transcript = await stt.transcribe(audio_bytes, audio.filename or "audio.wav")

    # ML 서비스 장애 시 fallback 없음 — Issue #43 (US-14)에서 별도 처리 예정
    ml_result = await ml.predict(audio_bytes or b"", transcript or "")
    tracks = get_tracks_by_indices(db, ml_result.track_indices)

    return RecommendResponse(
        tracks=[_to_track(t) for t in tracks],
        transcript=transcript,
        emotions=ml_result.emotions,
    )
