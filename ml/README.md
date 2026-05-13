# ML (머신러닝)

## 목적

wav2vec2 기반 음성 감정 분류 모델 학습 및 서빙

## 현황

⏳ Sprint #2 의 US-6 (EmotionClassifier) 작업에서 본격 구체화 예정. 현재는 placeholder 디렉터리입니다.

## 예정 구조

- `train/` — 학습 스크립트 (캐글 emotion-dataset-audio 사용)
- `serve/` — 추론 서버 (FastAPI 백엔드에서 호출하는 별도 ML 서비스 또는 같은 프로세스 내 모듈)
- `tests/` — 단위 테스트

## 의존

- ADR-0002 (wav2vec2 채택)
- SRS v1 §7 (`EmotionClassifier` 컴포넌트)

## 관련 이슈

- 이슈 #2 폴더 구조의 `/ml` 항목 충족
