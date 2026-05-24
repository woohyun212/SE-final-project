from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MusicCatalog(Base):
    __tablename__ = "music_catalog"

    track_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    track_name: Mapped[str] = mapped_column(String(512), nullable=False)
    artists: Mapped[str] = mapped_column(Text, nullable=False)
    album_name: Mapped[str] = mapped_column(String(512), nullable=False)
    track_genre: Mapped[str] = mapped_column(String(128), nullable=False)
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    preview_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Audio features — similarity vector
    danceability: Mapped[float] = mapped_column(Float, nullable=False)
    energy: Mapped[float] = mapped_column(Float, nullable=False)
    valence: Mapped[float] = mapped_column(Float, nullable=False)
    acousticness: Mapped[float] = mapped_column(Float, nullable=False)
    instrumentalness: Mapped[float] = mapped_column(Float, nullable=False)
    speechiness: Mapped[float] = mapped_column(Float, nullable=False)
    liveness: Mapped[float] = mapped_column(Float, nullable=False)
    tempo: Mapped[float] = mapped_column(Float, nullable=False)
    loudness: Mapped[float] = mapped_column(Float, nullable=False)
    key: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[int] = mapped_column(Integer, nullable=False)
    time_signature: Mapped[int] = mapped_column(Integer, nullable=False)
