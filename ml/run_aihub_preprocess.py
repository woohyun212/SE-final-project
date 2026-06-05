"""
AIHub 한국어 감정 데이터 전처리 스크립트
데스크탑에서 실행:
    cd D:\School\SE-final-project\ml
    .venv\Scripts\python.exe run_aihub_preprocess.py --json <TL_02.실외 경로> --wav <TS_02.실외 경로>
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data.preprocess import _process_aihub

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIHub 감정 데이터 전처리")
    parser.add_argument("--json", required=True, help="AIHub 라벨링 JSON 폴더 (TL_02.실외)")
    parser.add_argument("--wav",  required=True, help="AIHub 원천 WAV 폴더 (TS_02.실외)")
    parser.add_argument("--dst",  default="data/raw", help="출력 폴더 (기본: data/raw)")
    parser.add_argument("--max",  type=int, default=500, help="레이블당 최대 샘플 수 (기본: 500)")
    args = parser.parse_args()

    json_dir = Path(args.json)
    wav_dir  = Path(args.wav)
    dst_dir  = Path(args.dst)

    print(f"JSON: {json_dir}")
    print(f"WAV:  {wav_dir}")
    print(f"출력: {dst_dir}")
    print(f"레이블당 최대: {args.max}개")
    print("전처리 시작...")

    n = _process_aihub(json_dir, wav_dir, dst_dir, max_per_label=args.max)
    print(f"\n완료: 총 {n}개 파일 → {dst_dir}")
