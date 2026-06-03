"""
emotion-dataset-audio → data/raw/<label>/ 구조로 재정리.

Usage:
    # 영어 데이터셋 (CREMA-D / TESS / Ravdess / Savee)
    python data/preprocess.py --src data/raw/emotion-dataset --dst data/raw

    # AIHub 한국어 감정 데이터 추가
    python data/preprocess.py --aihub-json <TL_02.실외 폴더> --aihub-wav <TS_02.실외 폴더> --dst data/raw
"""

import argparse
import json
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


# ── AIHub 한국어 감정 데이터 ────────────────────────────────────────────────────
AIHUB_MAP = {
    "기쁨": "happy", "화남": "angry", "슬픔": "sad",
    "공포": "fear",  "혐오": "disgust", "놀람": "surprise",
    "없음": "neutral",
}
AIHUB_SR = 16_000
AIHUB_MIN_SEC = 1.0      # 1초 미만 발화 제외
AIHUB_MAX_PER_LABEL = 2000  # 레이블당 최대 샘플 수 (불균형 방지)


def _process_aihub(json_dir: Path, wav_dir: Path, dst: Path, max_per_label: int = AIHUB_MAX_PER_LABEL) -> int:
    """AIHub JSON 라벨 + WAV → 발화 단위로 잘라 data/raw/<label>/ 에 저장."""
    try:
        import numpy as np
        import soundfile as sf
    except ImportError:
        raise RuntimeError("soundfile/numpy 필요: pip install soundfile numpy")

    counts: dict[str, int] = {label: 0 for label in LABELS}
    total = 0

    for json_path in sorted(json_dir.glob("*.json")):
        wav_path = wav_dir / (json_path.stem + ".wav")
        if not wav_path.exists():
            continue

        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        # WAV 로드 (stereo → mono, 48kHz → 16kHz)
        try:
            audio, sr = sf.read(str(wav_path))
        except Exception:
            continue
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != AIHUB_SR:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=AIHUB_SR)
            sr = AIHUB_SR

        for utt in meta.get("Conversation", []):
            # 약한 감정 제외
            if utt.get("VerifyEmotionLevel") == "약함":
                continue

            emotion_kr = utt.get("VerifyEmotionTarget", "없음")
            label = AIHUB_MAP.get(emotion_kr)
            if label is None:
                continue
            if counts[label] >= max_per_label:
                continue

            start = float(utt.get("StartTime", 0))
            end = float(utt.get("EndTime", 0))
            if end - start < AIHUB_MIN_SEC:
                continue

            s_idx = int(start * sr)
            e_idx = int(end * sr)
            segment = audio[s_idx:e_idx].astype("float32")
            if len(segment) < int(AIHUB_MIN_SEC * sr):
                continue

            out_dir = dst / label
            out_dir.mkdir(parents=True, exist_ok=True)
            fname = f"aihub_{json_path.stem}_{utt['TextNo']}.wav"
            sf.write(str(out_dir / fname), segment, sr)
            counts[label] += 1
            total += 1

    print("  AIHub 레이블별:", {k: v for k, v in counts.items() if v > 0})
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="")
    parser.add_argument("--dst", default="data/raw")
    parser.add_argument("--aihub-json", default="", help="AIHub 라벨링 JSON 폴더")
    parser.add_argument("--aihub-wav",  default="", help="AIHub 원천 WAV 폴더")
    parser.add_argument("--aihub-max",  type=int, default=AIHUB_MAX_PER_LABEL, help="AIHub 레이블당 최대 샘플 수")
    args = parser.parse_args()

    dst = Path(args.dst)
    total = 0

    if args.src:
        src = Path(args.src)
        print(f"src: {src}")
        for name, fn in [
            ("CREMA-D",  _process_crema),
            ("TESS",     _process_tess),
            ("Ravdess",  _process_ravdess),
            ("Savee",    _process_savee),
        ]:
            n = fn(src, dst)
            print(f"  {name}: {n}개")
            total += n

    if args.aihub_json and args.aihub_wav:
        print(f"\nAIHub json: {args.aihub_json}")
        print(f"AIHub wav:  {args.aihub_wav}")
        n = _process_aihub(Path(args.aihub_json), Path(args.aihub_wav), dst, args.aihub_max)
        print(f"  AIHub: {n}개")
        total += n

    print(f"\n완료: 총 {total}개 파일 → {dst}/<label>/")
    for label in sorted(LABELS):
        count = len(list((dst / label).glob("*.wav"))) if (dst / label).exists() else 0
        print(f"  {label}: {count}개")


if __name__ == "__main__":
    main()
