<!-- Generated: 2026-05-11 | Updated: 2026-05-11 -->

# SE-final-project

## Purpose
CWNU 컴퓨터공학과 3학년 1학기 **소프트웨어 공학** 기말 프로젝트 저장소.
주제는 **AI 기반 감정 분석 음악 추천 시스템** — 사용자의 음성 입력을 ML 감정 분류와 LLM 맥락 분석으로 융합 처리하여
Spotify/YouTube 카탈로그에서 음악을 추천하고, 감정-음악 2D 차트와 LLM 추천 이유를 함께 제시하는 Electron 데스크탑 애플리케이션이다.

현재 단계는 **요구사항 정의 및 설계 문서화 단계**이며, 소스 코드는 아직 작성되지 않았다.
저장소에는 강의 안내서, 라이선스, 그리고 `docs/회의록/` 디렉터리의 회의록 및 SRS 설계 패키지가 들어 있다.

## Key Files
| File | Description |
|------|-------------|
| `README.md` | 프로젝트 한 줄 소개 (CWNU CE 3학년 소프트웨어 공학 기말 프로젝트) |
| `LICENSE` | MIT License (Copyright (c) 2026 w00) |
| `.gitignore` | Python 중심의 표준 무시 패턴 (가상환경, 캐시, 빌드 산출물 등) |
| `26SS-SE-조별과제안내.pdf` | 강의 측에서 배포한 조별과제 안내서 (요구사항/평가 기준 원본) |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `docs/` | 모든 프로젝트 문서의 컨테이너. 현재는 `docs/회의록/` 하위에 회의록·SRS·다이어그램·ADR이 있다 (see `docs/AGENTS.md`) |
| `.omc/` | oh-my-claudecode 런타임 상태 (state, plans, logs) — 직접 수정 금지 |

## For AI Agents

### Working In This Directory
- **이 저장소의 단일 진실 공급원(SSOT)은 `docs/회의록/design/srs-v1.md` 이다.** 코드를 추가하거나 설계를 바꾸기 전에 반드시 SRS를 먼저 확인하라. 디렉터리 네비게이션은 `docs/회의록/README.md` 참조.
- 프로젝트 문서는 **한국어**로 작성된다. 새 문서/주석/커밋 메시지도 가능한 한 한국어 톤을 유지하라 (영어 코드 식별자는 영어 유지).
- 컴포넌트 명칭은 SRS §7 "도메인 어휘" 표를 그대로 사용하라:
  `VoiceCapture`, `EmotionClassifier`, `STTService`, `ContextAnalyzer`, `EmotionFusion`,
  `RecommendationEngine`, `MusicCatalog`, `FeedbackLogger`, `RecommendationVisualizer`, `CatalogSynchronizer`.
  이름이 흔들리면 후속 다이어그램/코드가 어긋난다.
- 핵심 유스케이스는 **UC-03 (음성으로 음악 추천 받기)** 이다. 다른 기능 결정 시 항상 UC-03의 P95 ≤ 3초 제약(NFR1.1)을 우선 고려하라.
- **캐글 dataset은 시스템 컨텍스트에 포함되지 않는다** — 학습 시점에만 사용되며 운영 중에는 `EmotionClassifier` 모델 가중치로 흡수된다.
  외부 시스템 다이어그램에 그리지 말 것.
- 새 소스 코드를 추가할 때는 SRS의 컴포넌트 위치 (Client / Backend / ML Server) 구분에 맞춰 디렉터리를 분리하라.
- 디렉터리/파일명에 한글이 포함될 수 있다 (`docs/회의록/`). 셸 명령에서는 반드시 따옴표로 감쌀 것.

### Testing Requirements
- 현재 단계: 코드 부재. 단위 테스트 기준선은 **NFR4.4 — 단위/통합 테스트 커버리지 ≥ 70%** 이다 (구현 단계 진입 시 적용).
- ML 모델 정확도: 캐글 테스트셋 기준 **≥ 70%** (NFR4.3).
- 추천 품질: Precision@10 ≥ 0.4, 좋아요율 ≥ 50% (NFR4.1–4.2).
- 성능 검증: 음성 전송→추천 응답 P95 ≤ 3초, 동시 사용자 100명 부하 테스트 (NFR1.1–1.2).

### Common Patterns
- 외부 API 호출 (Spotify / LLM / YouTube)은 모두 **fallback 경로**를 함께 설계한다 (NFR2.3, NFR2.4, UC-03 A1–A3 참조).
- 음성 원본은 분석 후 **즉시 폐기**하고 감정 벡터만 저장 (NFR3.2). STT 텍스트는 동의 시에만 저장 (NFR3.3).
- 비밀번호 저장은 **bcrypt cost ≥ 12** (NFR3.4), API 키는 환경변수 (NFR3.5).
- 모든 통신은 TLS 1.2+ (NFR3.1).

## Dependencies

### Internal
- 모든 설계 결정은 `docs/회의록/design/srs-v1.md` 와 `docs/회의록/design/diagrams/` 의 SVG 2종, 그리고 `docs/회의록/decisions/` 의 ADR 목록에 근거한다.

### External (예정)
- **Electron** — 크로스플랫폼 데스크탑 클라이언트
- **Spotify Web API** — 트랙 메타 + audio features (메인 카탈로그 소스)
- **LLM API** — STT 결과 맥락 분석 + 추천 이유 생성
- **YouTube Data API** — 감성 플리에서 시드 트랙 추출 (카탈로그 동기화 시)
- **Kaggle Emotion Dataset (Audio)** — `EmotionClassifier` 학습용 (운영 시 사용 안 함)

### Tooling
- Python (.gitignore에 따라 백엔드/ML은 Python 스택으로 추정)
- Git (현재 브랜치: `main`, 작성자: woohyun)

## Project State (2026-05-11 기준)
- ✅ 주제 확정, 요구사항 초안 (`docs/회의록/meetings/2026/2026-05-11-week1-kickoff.md`)
- ✅ SRS v1 작성 (`docs/회의록/design/srs-v1.md`)
- ✅ 시스템 컨텍스트 / 유스케이스 다이어그램 (`docs/회의록/design/diagrams/`)
- ✅ ADR-0001 Accepted — Electron 클라이언트 채택 (`docs/회의록/decisions/0001-electron-as-client-platform.md`)
- ⏳ 아키텍처/클래스/시퀀스 다이어그램
- ⏳ 소스 코드 (Electron 클라이언트, 백엔드 API, ML 서버)
- ⏳ CI/CD, Blue-Green 배포 파이프라인

<!-- MANUAL: 이 라인 아래의 수동 주석은 재생성 시에도 보존됩니다. -->
