"""
/recommend 수동 테스트 스크립트

실제 Whisper STT로 음성을 텍스트로 변환하고,
ML 클라이언트는 더미 응답을 반환해 /recommend 응답 결과를 확인합니다.

Usage:
    python -m scripts.test_recommend_manual <path/to/audio.wav> [--valence V] [--arousal A] [--dominance D]

Example:
    python -m scripts.test_recommend_manual audio.wav
    python -m scripts.test_recommend_manual audio.wav --valence 0.8 --arousal 0.6 --dominance 0.5
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
from app.services.ml_client import MLClient, VADResult, get_ml_client  # noqa: E402


def _make_dummy_ml(valence: float, arousal: float, dominance: float) -> MLClient:
    mock = MagicMock(spec=MLClient)
    mock.predict = AsyncMock(
        return_value=VADResult(valence=valence, arousal=arousal, dominance=dominance)
    )
    return mock


def main() -> None:
    parser = argparse.ArgumentParser(description="/recommend 수동 테스트")
    parser.add_argument("wav", type=Path, help="테스트할 WAV 파일 경로")
    parser.add_argument("--valence", type=float, default=0.5, help="더미 VAD valence (기본: 0.5)")
    parser.add_argument("--arousal", type=float, default=0.5, help="더미 VAD arousal (기본: 0.5)")
    parser.add_argument("--dominance", type=float, default=0.5, help="더미 VAD dominance (기본: 0.5)")
    args = parser.parse_args()

    if not args.wav.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {args.wav}")
        sys.exit(1)

    audio_bytes = args.wav.read_bytes()
    print(f"\n{'='*50}")
    print(f"  파일  : {args.wav}  ({len(audio_bytes):,} bytes)")
    print(f"  더미 ML VAD  : valence={args.valence}  arousal={args.arousal}  dominance={args.dominance}")
    print(f"{'='*50}\n")

    app.dependency_overrides[get_ml_client] = lambda: _make_dummy_ml(args.valence, args.arousal, args.dominance)

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

    print("─── 맥락 분석 (ContextAnalyzer) ────────────")
    context = body.get("context") or {}
    if context:
        for k, v in context.items():
            print(f"  {k:<16} {v}")
    else:
        print("  (없음)")
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
