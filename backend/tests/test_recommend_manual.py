"""
/recommend 수동 테스트 스크립트

실제 Whisper STT로 음성을 텍스트로 변환하고,
ML 클라이언트는 더미 응답을 반환해 /recommend 응답 결과를 확인합니다.

Usage:
    python -m scripts.test_recommend_manual <path/to/audio.wav> [--indices 1 2 3 ...]

Example:
    python -m scripts.test_recommend_manual audio.wav
    python -m scripts.test_recommend_manual audio.wav --indices 1 5 10 20
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.ml_client import MLClient, MLResult, get_ml_client  # noqa: E402

DUMMY_EMOTIONS = {
    "happy": 0.75,
    "energetic": 0.80,
    "calm": 0.20,
    "sad": 0.10,
}


def _make_dummy_ml(indices: list[int]) -> MLClient:
    mock = MagicMock(spec=MLClient)
    mock.predict = AsyncMock(
        return_value=MLResult(track_indices=indices, emotions=DUMMY_EMOTIONS)
    )
    return mock


def main() -> None:
    parser = argparse.ArgumentParser(description="/recommend 수동 테스트")
    parser.add_argument("wav", type=Path, help="테스트할 WAV 파일 경로")
    parser.add_argument(
        "--indices",
        nargs="+",
        type=int,
        default=list(range(1, 11)),
        metavar="N",
        help="ML 더미 응답으로 사용할 track id 목록 (기본: 1~10)",
    )
    args = parser.parse_args()

    if not args.wav.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {args.wav}")
        sys.exit(1)

    audio_bytes = args.wav.read_bytes()
    print(f"\n{'='*50}")
    print(f"  파일  : {args.wav}  ({len(audio_bytes):,} bytes)")
    print(f"  더미 ML indices : {args.indices}")
    print(f"  더미 ML emotions: {DUMMY_EMOTIONS}")
    print(f"{'='*50}\n")

    app.dependency_overrides[get_ml_client] = lambda: _make_dummy_ml(args.indices)

    print("[1/3] FastAPI TestClient 초기화 중...")
    with TestClient(app) as client:
        print("[2/3] Whisper STT + /recommend 호출 중  (STT가 처음이면 모델 로딩에 시간이 걸립니다)")
        res = client.post(
            "/recommend",
            files={"audio": (args.wav.name, audio_bytes, "audio/wav")},
        )

    app.dependency_overrides.clear()

    print(f"[3/3] 응답 수신  (HTTP {res.status_code})\n")

    if res.status_code != 200:
        print("[ERROR] 요청 실패:")
        print(res.text)
        sys.exit(1)

    body = res.json()

    print("─── STT 결과 ───────────────────────────────")
    print(f"  transcript : {body.get('transcript') or '(없음)'}\n")

    print("─── 감정 분석 (ML 더미) ────────────────────")
    emotions = body.get("emotions") or {}
    for k, v in emotions.items():
        bar = "█" * int(v * 20)
        print(f"  {k:<12} {v:.2f}  {bar}")
    print()

    print("─── 추천 트랙 ──────────────────────────────")
    tracks = body.get("tracks", [])
    if not tracks:
        print("  (결과 없음 — DB에 해당 index의 곡이 없을 수 있습니다)")
    for i, t in enumerate(tracks, 1):
        print(f"  {i:2}. [{t['track_id']}] {t['title']} — {t['artist']}")
        print(f"      앨범: {t['album']}  /  {t['duration_sec']}초")
    print()

    print("─── 전체 JSON 응답 ─────────────────────────")
    print(json.dumps(body, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
