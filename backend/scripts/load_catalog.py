"""Kaggle Spotify Tracks Dataset → MusicCatalog DB 적재 스크립트 (US-9).

Usage:
    python scripts/load_catalog.py [--csv PATH] [--batch-size N]

기본 CSV 경로: backend/data/dataset.csv
"""

import argparse
import csv
import os
import sys
from pathlib import Path

# backend 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.music_catalog import MusicCatalog

DEFAULT_CSV = Path(__file__).parent.parent / "data" / "dataset.csv"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/se_project")


def _parse_row(row: dict) -> MusicCatalog | None:
    track_id = row.get("track_id", "").strip()
    if not track_id:
        return None
    try:
        return MusicCatalog(
            track_id=track_id,
            track_name=row["track_name"][:512],
            artists=row["artists"][:1024],
            album_name=row["album_name"][:512],
            track_genre=row["track_genre"][:128],
            popularity=int(row.get("popularity") or 0),
            duration_ms=int(row["duration_ms"]),
            preview_url=None,
            danceability=float(row["danceability"]),
            energy=float(row["energy"]),
            valence=float(row["valence"]),
            acousticness=float(row["acousticness"]),
            instrumentalness=float(row["instrumentalness"]),
            speechiness=float(row["speechiness"]),
            liveness=float(row["liveness"]),
            tempo=float(row["tempo"]),
            loudness=float(row["loudness"]),
            key=int(row["key"]),
            mode=int(row["mode"]),
            time_signature=int(row["time_signature"]),
        )
    except (KeyError, ValueError):
        return None


def load(csv_path: Path, batch_size: int = 1000) -> None:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE music_catalog"))
        conn.commit()

    inserted = 0
    skipped = 0
    seen: set[str] = set()
    batch: list[MusicCatalog] = []

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        with Session(engine) as session:
            for row in reader:
                track_id = row.get("track_id", "").strip()
                if not track_id or track_id in seen:
                    skipped += 1
                    continue
                seen.add(track_id)

                obj = _parse_row(row)
                if obj is None:
                    skipped += 1
                    continue

                batch.append(obj)
                if len(batch) >= batch_size:
                    session.bulk_save_objects(batch)
                    session.commit()
                    inserted += len(batch)
                    print(f"  {inserted:,}곡 적재 완료...")
                    batch.clear()

            if batch:
                session.bulk_save_objects(batch)
                session.commit()
                inserted += len(batch)

    print(f"\n완료: {inserted:,}곡 적재, {skipped:,}곡 스킵")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"CSV 파일을 찾을 수 없습니다: {args.csv}")
        sys.exit(1)

    print(f"CSV: {args.csv}")
    print(f"DB:  {DATABASE_URL}\n")
    load(args.csv, args.batch_size)
