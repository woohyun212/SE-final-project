"""
emotion-dataset-audio → data/raw/<label>/ 구조로 재정리.

Usage:
    python data/preprocess.py [--src data/raw/emotion-dataset] [--dst data/raw]
"""

import argparse
import shutil
from pathlib import Path

# 공통 레이블 (dataset.py의 EMOTION_LABELS와 동일)
LABELS = {"angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"}

# ── CREMA-D ──────────────────────────────────────────────────────────────────
CREMA_MAP = {
    "ANG": "angry", "DIS": "disgust", "FEA": "fear",
    "HAP": "happy", "NEU": "neutral", "SAD": "sad",
}

def _process_crema(src: Path, dst: Path) -> int:
    count = 0
    for f in (src / "CREMA-D" / "AudioWAV").glob("*.wav"):
        parts = f.stem.split("_")
        if len(parts) < 3:
            continue
        label = CREMA_MAP.get(parts[2])
        if label:
            (dst / label).mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst / label / f"crema_{f.name}")
            count += 1
    return count

# ── TESS ─────────────────────────────────────────────────────────────────────
TESS_MAP = {
    "angry": "angry", "disgust": "disgust", "fear": "fear",
    "happy": "happy", "neutral": "neutral", "sad": "sad",
    "pleasant_surprise": "surprise", "surprise": "surprise",
}

def _process_tess(src: Path, dst: Path) -> int:
    count = 0
    for folder in (src / "Tess").glob("*_*"):
        key = folder.name.split("_", 1)[-1].lower()
        label = TESS_MAP.get(key)
        if not label:
            continue
        for f in folder.glob("*.wav"):
            (dst / label).mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst / label / f"tess_{f.name}")
            count += 1
    return count

# ── RAVDESS ───────────────────────────────────────────────────────────────────
RAVDESS_MAP = {
    "01": "neutral", "03": "happy", "04": "sad",
    "05": "angry",   "06": "fear",  "07": "disgust", "08": "surprise",
    # 02=calm 제외
}

def _process_ravdess(src: Path, dst: Path) -> int:
    count = 0
    for wav in (src / "Ravdess").rglob("*.wav"):
        parts = wav.stem.split("-")
        if len(parts) < 3:
            continue
        label = RAVDESS_MAP.get(parts[2])
        if label:
            (dst / label).mkdir(parents=True, exist_ok=True)
            shutil.copy2(wav, dst / label / f"ravdess_{wav.name}")
            count += 1
    return count

# ── SAVEE ─────────────────────────────────────────────────────────────────────
SAVEE_MAP = {
    "a": "angry", "d": "disgust", "f": "fear",
    "h": "happy", "n": "neutral", "sa": "sad", "su": "surprise",
}

def _process_savee(src: Path, dst: Path) -> int:
    count = 0
    for f in (src / "Savee").glob("*.wav"):
        stem = f.stem  # e.g. DC_a01
        if "_" not in stem:
            continue
        code = stem.split("_")[1].rstrip("0123456789")
        label = SAVEE_MAP.get(code.lower())
        if label:
            (dst / label).mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst / label / f"savee_{f.name}")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="data/raw/emotion-dataset")
    parser.add_argument("--dst", default="data/raw")
    args = parser.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)

    print(f"src: {src}")
    print(f"dst: {dst}")

    total = 0
    for name, fn in [
        ("CREMA-D",  _process_crema),
        ("TESS",     _process_tess),
        ("Ravdess",  _process_ravdess),
        ("Savee",    _process_savee),
    ]:
        n = fn(src, dst)
        print(f"  {name}: {n}개")
        total += n

    print(f"\n완료: 총 {total}개 파일 → {dst}/<label>/")
    for label in sorted(LABELS):
        count = len(list((dst / label).glob("*.wav"))) if (dst / label).exists() else 0
        print(f"  {label}: {count}개")


if __name__ == "__main__":
    main()
