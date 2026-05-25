# ML — EmotionClassifier

wav2vec2 기반 음성 감정 분류 모델 학습 및 서빙. (Issue #32, Sprint 2)

## 구조

```
ml/
├── data/
│   ├── download.sh     # 캐글 데이터셋 다운로드
│   └── raw/            # 다운로드된 데이터 (gitignore)
├── train/
│   ├── dataset.py      # 데이터 로딩, 전처리, 레이블 정의
│   ├── model.py        # wav2vec2 모델 빌드
│   └── train.py        # 학습 스크립트
├── serve/
│   ├── app.py          # FastAPI 추론 서버 (POST /ml/predict)
│   └── predictor.py    # 모델 로드 및 추론 로직
├── tests/
│   └── test_predictor.py
├── model/              # 학습된 모델 저장 위치 (gitignore)
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
└── Makefile
```

## 빠른 시작

```bash
cd ml/

# 1. 의존성 설치
make install-dev

# 2. 캐글 데이터셋 다운로드
#    사전 조건: ~/.kaggle/kaggle.json 필요
#    발급: https://www.kaggle.com/settings > API > Create New Token
make download-data

# 3. 학습
make train

# 4. 추론 서버 실행 (포트 8001)
make serve

# 5. 테스트
make test
```

## 데이터셋

- **출처**: [seungjunlim/emotion-dataset-audio](https://www.kaggle.com/datasets/seungjunlim/emotion-dataset-audio)
- **구조 가정**: `data/raw/<label>/<file>.wav`
- **레이블**: angry, disgust, fear, happy, neutral, sad, surprise
- 다운로드 후 실제 디렉터리 구조 확인하여 `train/dataset.py`의 `EMOTION_LABELS`, `scan_dataset()` 수정

## 목표 지표 (NFR4.3)

| 지표 | 목표 |
|---|---|
| 캐글 테스트셋 정확도 | ≥ 70% |
| 추론 시간 | ≤ 1.5초 (NFR1.3) |

## API

```
POST /ml/predict
Content-Type: multipart/form-data
Body: audio=<WAV/WebM 파일>

Response:
{
  "label": "happy",
  "valence": 0.8,
  "arousal": 0.6,
  "dominance": 0.5,
  "probabilities": { "happy": 0.82, "neutral": 0.10, ... }
}
```

## 의존

- ADR-0002 (wav2vec2 채택)
- Issue #32 (US-6 EmotionClassifier)
- Issue #34 (US-8 감정 벡터 → 유사도 매칭, 이 서버 출력을 소비)
