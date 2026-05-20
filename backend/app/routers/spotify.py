from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.spotify import AudioFeatures, TrackSearchResponse
from app.services.spotify import RateLimitError, get_audio_features, search_tracks

router = APIRouter(prefix="/spotify", tags=["spotify"])


@router.get("/search", response_model=TrackSearchResponse)
async def spotify_search(
    q: str = Query(..., min_length=1, description="검색 쿼리"),
    limit: int = Query(10, ge=1, le=50, description="결과 수"),
    offset: int = Query(0, ge=0, description="페이지 오프셋"),
) -> TrackSearchResponse:
    """Spotify 트랙 검색"""
    try:
        result = await search_tracks(q, limit=limit, offset=offset)
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Spotify rate limit — {e.retry_after}초 후 재시도하세요.",
            headers={"Retry-After": str(e.retry_after)},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return TrackSearchResponse(**result)


@router.get("/audio-features/{track_id}", response_model=AudioFeatures)
async def spotify_audio_features(track_id: str) -> AudioFeatures:
    """Spotify 트랙의 audio features 조회"""
    try:
        data = await get_audio_features(track_id)
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Spotify rate limit — {e.retry_after}초 후 재시도하세요.",
            headers={"Retry-After": str(e.retry_after)},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return AudioFeatures(**data)
