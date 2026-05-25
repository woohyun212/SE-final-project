"""Kaggle Spotify Tracks Dataset → MusicCatalog DB 적재 스크립트 (US-9).

Usage:
    python -m scripts.load_catalog [--csv PATH] [--batch-size N] [--truncate]

기본 CSV 경로: backend/data/dataset.csv
--truncate 없이 실행하면 ON CONFLICT DO NOTHING (UPSERT) 으로 동작합니다.
"""

import argparse
import csv
import logging
import os
import sys
from pathlib import Path

# backend 루트를 sys.path에 추가 (패키지 설치 없이 실행 시)
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models.music_catalog import MusicCatalog  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_CSV = Path(__file__).parent.parent / "data" / "dataset.csv"

_url = os.getenv("DATABASE_URL")
if not _url:
    raise RuntimeError(
        "DATABASE_URL 환경변수가 설정되지 않았습니다. .env 파일 또는 환경변수를 확인하세요."
    )
DATABASE_URL: str = _url


def _parse_row(row: dict, row_num: int) -> dict | None:
    track_id = row.get("track_id", "").strip()
    if not track_id:
        return None
    try:
        track_name = row["track_name"]
        artists = row["artists"]
        if len(track_name) > 512:
            logger.debug("row %d track_id=%s: track_name %d자 → 512자 truncation", row_num, track_id, len(track_name))
        if len(artists) > 1024:
            logger.debug("row %d track_id=%s: artists %d자 → 1024자 truncation", row_num, track_id, len(artists))
        return {
            "track_id": track_id,
            "track_name": track_name[:512],
            "artists": artists[:1024],
            "album_name": row["album_name"][:512],
            "track_genre": row["track_genre"][:128],
            "popularity": int(row.get("popularity") or 0),
            "duration_ms": int(row["duration_ms"]),
            "preview_url": row.get("preview_url") or None,
            "danceability": float(row["danceability"]),
            "energy": float(row["energy"]),
            "valence": float(row["valence"]),
            "acousticness": float(row["acousticness"]),
            "instrumentalness": float(row["instrumentalness"]),
            "speechiness": float(row["speechiness"]),
            "liveness": float(row["liveness"]),
            "tempo": float(row["tempo"]),
            "loudness": float(row["loudness"]),
            "key": int(row["key"]),
            "mode": int(row["mode"]),
            "time_signature": int(row["time_signature"]),
        }
    except (KeyError, ValueError) as exc:
        logger.warning("row %d track_id=%s 파싱 실패: %s", row_num, track_id, exc)
        return None


def load(csv_path: Path, batch_size: int = 1000, truncate: bool = False) -> None:
    engine = create_engine(DATABASE_URL)

    if truncate:
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE music_catalog"))
            conn.commit()
        logger.info("music_catalog TRUNCATE 완료")

    inserted = 0
    skipped = 0
    seen: set[str] = set()
    batch: list[dict] = []

    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        with Session(engine) as session:
            for row_num, row in enumerate(reader, start=1):
                track_id = row.get("track_id", "").strip()
                if not track_id or track_id in seen:
                    skipped += 1
                    continue
                seen.add(track_id)

                record = _parse_row(row, row_num)
                if record is None:
                    skipped += 1
                    continue

                batch.append(record)
                if len(batch) >= batch_size:
                    stmt = pg_insert(MusicCatalog).on_conflict_do_nothing(index_elements=["track_id"])
                    session.execute(stmt, batch)
                    session.commit()
                    inserted += len(batch)
                    logger.info("  %s곡 적재 완료...", f"{inserted:,}")
                    batch.clear()

            if batch:
                stmt = pg_insert(MusicCatalog).on_conflict_do_nothing(index_elements=["track_id"])
                session.execute(stmt, batch)
                session.commit()
                inserted += len(batch)

    logger.info("완료: %s곡 적재, %s곡 스킵", f"{inserted:,}", f"{skipped:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="적재 전 music_catalog 테이블 전체 삭제 (기본 OFF — ON CONFLICT DO NOTHING 동작)",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        logger.error("CSV 파일을 찾을 수 없습니다: %s", args.csv)
        sys.exit(1)

    logger.info("CSV: %s", args.csv)
    logger.info("DB:  %s", DATABASE_URL)
    load(args.csv, args.batch_size, args.truncate)
