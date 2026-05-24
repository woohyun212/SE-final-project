from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from app.schemas.recommend import RecommendResponse, Track
from app.services.recommendation import SUPPORTED_EMOTIONS, recommend_by_emotion
from app.services.spotify import RateLimitError, SpotifyCredentialsError

router = APIRouter(prefix="/recommend", tags=["recommend"])


@router.post("", response_model=RecommendResponse)
async def recommend(
    audio: UploadFile,
    emotion: str = Query(
        "neutral",
        description=f"감지된 감정 레이블. 지원 값: {', '.join(SUPPORTED_EMOTIONS)}",
    ),
) -> RecommendResponse:
    """감정 벡터를 Spotify 카탈로그에 코사인 유사도로 매핑해 상위 10개 트랙 반환 (US-8)."""
    try:
        tracks_data = await recommend_by_emotion(emotion)
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Spotify rate limit — {e.retry_after}초 후 재시도하세요.",
            headers={"Retry-After": str(e.retry_after)},
        )
    except SpotifyCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return RecommendResponse(
        tracks=[
            Track(
                title=t.get("name", ""),
                artist=", ".join(t.get("artists") or []),
                album=t.get("album", ""),
                duration_sec=t.get("duration_ms", 0) // 1000,
                track_id=t.get("track_id"),
                preview_url=t.get("preview_url"),
            )
            for t in tracks_data
        ]
    )
