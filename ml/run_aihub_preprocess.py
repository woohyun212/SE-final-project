"""
AIHub 한국어 감정 데이터 전처리 스크립트
데스크탑에서 실행:
    cd D:\School\SE-final-project\ml
    .venv\Scripts\python.exe run_aihub_preprocess.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data.preprocess import _process_aihub

JSON_DIR = Path(r"C:\Users\Pongc\Downloads\134-1.감정이 태깅된 자유대화 (성인)\01-1.정식개방데이터\Training\02.라벨링데이터\TL_02.실외")
WAV_DIR  = Path(r"C:\Users\Pongc\Downloads\134-1.감정이 태깅된 자유대화 (성인)\01-1.정식개방데이터\Training\01.원천데이터\TS_02.실외")
DST_DIR  = Path(__file__).parent / "aihub_processed"

if __name__ == "__main__":
    print(f"JSON: {JSON_DIR}")
    print(f"WAV:  {WAV_DIR}")
    print(f"출력: {DST_DIR}")
    print("전처리 시작 (30-60분 소요)...")

    n = _process_aihub(JSON_DIR, WAV_DIR, DST_DIR, max_per_label=500)
    print(f"\n완료: 총 {n}개 파일 → {DST_DIR}")
