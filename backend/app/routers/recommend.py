from fastapi import APIRouter, UploadFile

from app.schemas.recommend import RecommendResponse, Track

router = APIRouter(prefix="/recommend", tags=["recommend"])

_DUMMY_TRACKS: list[Track] = [
    Track(title="Weightless", artist="Marconi Union", album="Weightless", duration_sec=480),
    Track(title="Clair de Lune", artist="Claude Debussy", album="Suite bergamasque", duration_sec=299),
    Track(title="Breathe (2 AM)", artist="Anna Nalick", album="Wreck of the Day", duration_sec=235),
    Track(title="River Flows in You", artist="Yiruma", album="First Love", duration_sec=211),
    Track(title="Experience", artist="Ludovico Einaudi", album="In a Time Lapse", duration_sec=344),
]


@router.post("", response_model=RecommendResponse)
async def recommend(audio: UploadFile) -> RecommendResponse:
    return RecommendResponse(tracks=_DUMMY_TRACKS)
