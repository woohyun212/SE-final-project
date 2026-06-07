import asyncio
import logging
import time

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationResult, RecommendationSession
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
from app.services.ml_client import MLClient, VADResult, get_ml_client, vad_from_text
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
    pipeline_start = time.perf_counter()
    audio_bytes = await audio.read()

    # STT와 ML predict는 둘 다 audio_bytes만 입력받는 독립 호출 — gather로 병렬 실행해
    # 두 단계 중 더 느린 쪽의 시간만 소요되도록 한다 (기존엔 순차 실행으로 합산되었음).
    async def _transcribe() -> str | None:
        if not audio_bytes:
            return None
        start = time.perf_counter()
        try:
            text = await stt.transcribe(audio_bytes, audio.filename or "audio.wav")
        except Exception as exc:
            logger.warning(
                "recommend stage=stt elapsed_ms=%.1f failed — context analysis will be skipped: %s",
                (time.perf_counter() - start) * 1000, exc,
            )
            return None
        logger.info("recommend stage=stt elapsed_ms=%.1f transcript_len=%d", (time.perf_counter() - start) * 1000, len(text))
        return text

    async def _predict() -> VADResult | None:
        start = time.perf_counter()
        try:
            result = await ml.predict(audio_bytes or b"")
        except Exception as exc:
            logger.warning(
                "recommend stage=ml elapsed_ms=%.1f failed — will fall back to text-based VAD: %s",
                (time.perf_counter() - start) * 1000, exc,
            )
            return None
        logger.info("recommend stage=ml elapsed_ms=%.1f", (time.perf_counter() - start) * 1000)
        return result

    transcript, ml_result = await asyncio.gather(_transcribe(), _predict())

    ml_fallback = ml_result is None
    vad = ml_result if ml_result is not None else vad_from_text(transcript or "")

    # ContextAnalyzer: 텍스트 → 맥락 (시간대/장소/활동/감정)
    context: ContextResult | None = None
    context_fallback = False
    if transcript and analyzer is not None:
        start = time.perf_counter()
        context, context_fallback = await analyzer.analyze(transcript)
        logger.info(
            "recommend stage=context_analyzer elapsed_ms=%.1f fallback=%s",
            (time.perf_counter() - start) * 1000, context_fallback,
        )

    # EmotionFusion: VAD + Context → Spotify 특징 공간
    emotion_vector = fuse(vad.valence, vad.arousal, vad.dominance, context)

    # RecommendationEngine: 코사인 유사도 + 누적 피드백 가중치 — (catalog, score) 튜플 리스트
    start = time.perf_counter()
    catalog_tracks = recommend_by_emotion(db, emotion_vector, user_id=current_user.id)
    logger.info(
        "recommend stage=recommendation_engine elapsed_ms=%.1f track_count=%d",
        (time.perf_counter() - start) * 1000, len(catalog_tracks),
    )

    # ReasonGenerator: 각 추천 곡에 대한 LLM 이유 생성
    reasons: dict[str, str] = {}
    reason_fallback = False
    if reason_gen is not None and catalog_tracks:
        start = time.perf_counter()
        reasons, reason_fallback = await reason_gen.generate(
            [t for t, _ in catalog_tracks],
            vad.valence,
            vad.arousal,
            vad.dominance,
            context,
        )
        logger.info(
            "recommend stage=reason_generator elapsed_ms=%.1f fallback=%s",
            (time.perf_counter() - start) * 1000, reason_fallback,
        )

    # RecommendationSession + 추천 결과 곡 DB 저장
    start = time.perf_counter()
    session = RecommendationSession(
        user_id=current_user.id,
        user_valence=emotion_vector["valence"],
        user_energy=emotion_vector["energy"],
    )
    db.add(session)
    db.flush()  # session.id 확보
    for rank, (track, score) in enumerate(catalog_tracks, start=1):
        db.add(RecommendationResult(
            session_id=session.id,
            track_id=track.track_id,
            rank=rank,
            score=round(score, 4),
        ))
    db.commit()
    logger.info("recommend stage=db_save elapsed_ms=%.1f", (time.perf_counter() - start) * 1000)

    logger.info("recommend stage=total elapsed_ms=%.1f session_id=%s", (time.perf_counter() - pipeline_start) * 1000, session.id)

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
