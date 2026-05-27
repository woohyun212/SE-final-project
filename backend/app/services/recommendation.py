from sqlalchemy.orm import Session

from app.models.music_catalog import MusicCatalog


def get_tracks_by_indices(db: Session, indices: list[int]) -> list[MusicCatalog]:
    if not indices:
        return []
    result_map = {
        r.id: r
        for r in db.query(MusicCatalog).filter(MusicCatalog.id.in_(indices)).all()
        if r.id is not None
    }
    return [result_map[i] for i in indices if i in result_map]
