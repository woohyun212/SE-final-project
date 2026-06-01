import logging

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationSession
from app.routers.auth import get_current_user
from app.schemas.context import ContextResult
from app.schemas.recommend import (
    EmotionVector,
    FallbackFlags,
    RecommendationItem,
    RecommendResponse,
    TrackInfo,
)
from app.services.context_analyzer import ContextAnalyzer, get_context_analyzer
from app.services.emotion_fusion import fuse
from app.services.ml_client import MLClient, get_ml_client, vad_from_text
from app.services.reason_generator import ReasonGenerator, get_reason_generator
from app.services.recommendation import recommend_by_emotion
from app.services.stt import STTProvider, get_stt_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommend", tags=["recommend"])


def _to_recommendation_item(
    catalog: MusicCatalog,
    score: float,
    reason: str | None,
) -> RecommendationItem:
    return RecommendationItem(
        track=TrackInfo(
            track_id=catalog.track_id,
            title=catalog.track_name,
            artist=catalog.artists,
            album=catalog.album_name,
            duration_sec=catalog.duration_ms // 1000,
            preview_url=catalog.preview_url,
        ),
        score=round(score, 4),
        reason=reason,
        track_features=EmotionVector(
            valence=round(catalog.valence, 3),
            energy=round(catalog.energy, 3),
        ),
    )


@router.post("", response_model=RecommendResponse)
async def recommend(
    audio: UploadFile,
    db: Session = Depends(get_db),
    stt: STTProvider = Depends(get_stt_provider),
    ml: MLClient = Depends(get_ml_client),
    analyzer: ContextAnalyzer | None = Depends(get_context_analyzer),
    reason_gen: ReasonGenerator | None = Depends(get_reason_generator),
    current_user=Depends(get_current_user),
) -> RecommendResponse:
    audio_bytes = await audio.read()

    # STT: 오디오 → 텍스트
    transcript: str | None = None
    if audio_bytes:
        transcript = await stt.transcribe(audio_bytes, audio.filename or "audio.wav")

    # ML: 오디오 → VAD 감정 벡터 (장애 시 transcript 키워드 기반 VAD로 대체)
    ml_fallback = False
    try:
        vad = await ml.predict(audio_bytes or b"")
    except Exception as exc:
        logger.warning("ML predict failed — text-based VAD fallback: %s", exc)
        vad = vad_from_text(transcript or "")
        ml_fallback = True

    # ContextAnalyzer: 텍스트 → 맥락 (시간대/장소/활동/감정)
    context: ContextResult | None = None
    context_fallback = False
    if transcript and analyzer is not None:
        context, context_fallback = await analyzer.analyze(transcript)

    # EmotionFusion: VAD + Context → Spotify 특징 공간
    emotion_vector = fuse(vad.valence, vad.arousal, vad.dominance, context)

    # RecommendationEngine: 코사인 유사도 — (catalog, score) 튜플 리스트
    catalog_tracks = recommend_by_emotion(db, emotion_vector)

    # ReasonGenerator: 각 추천 곡에 대한 LLM 이유 생성
    reasons: dict[str, str] = {}
    reason_fallback = False
    if reason_gen is not None and catalog_tracks:
        reasons, reason_fallback = await reason_gen.generate(
            [t for t, _ in catalog_tracks],
            vad.valence,
            vad.arousal,
            vad.dominance,
            context,
        )

    # RecommendationSession: DB에 세션 저장
    session = RecommendationSession(
        user_id=current_user.id,
        user_valence=emotion_vector["valence"],
        user_energy=emotion_vector["energy"],
    )
    db.add(session)
    db.commit()

    return RecommendResponse(
        session_id=session.id,
        recommendations=[
            _to_recommendation_item(track, score, reasons.get(track.track_id))
            for track, score in catalog_tracks
        ],
        user_emotion=EmotionVector(
            valence=round(emotion_vector["valence"], 3),
            energy=round(emotion_vector["energy"], 3),
        ),
        transcript=transcript,
        context=context,
        fallback_flags=FallbackFlags(ml=ml_fallback, context=context_fallback, reason=reason_fallback),
    )
