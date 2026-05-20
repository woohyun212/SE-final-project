#!/usr/bin/env bash
# 캐글 데이터셋 다운로드: seungjunlim/emotion-dataset-audio
# 사전 조건: kaggle.json을 ~/.kaggle/kaggle.json에 배치
#   발급: https://www.kaggle.com/settings > API > Create New Token
set -euo pipefail

DATASET="seungjunlim/emotion-dataset-audio"
OUT_DIR="$(dirname "$0")/raw"

if ! command -v kaggle &> /dev/null; then
    echo "kaggle CLI 없음. 'pip install kaggle' 실행 후 재시도."
    exit 1
fi

if [ ! -f "$HOME/.kaggle/kaggle.json" ]; then
    echo "~/.kaggle/kaggle.json 없음. 캐글 계정에서 API 토큰 발급 필요."
    exit 1
fi

chmod 600 "$HOME/.kaggle/kaggle.json"

mkdir -p "$OUT_DIR"
kaggle datasets download -d "$DATASET" -p "$OUT_DIR" --unzip
echo "다운로드 완료: $OUT_DIR"
