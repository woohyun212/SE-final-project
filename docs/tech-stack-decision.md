# 기술 스택 결정 (Tech Stack Decision)

> **요약 카탈로그.** 결정의 *근거*와 alternatives, consequences는 [ADR-0002](./회의록/decisions/0002-tech-stack.md) 가 단일 진실 소스(SSOT)다.
> 이 문서는 새로 합류한 팀원이 30초 안에 "지금 스택이 뭔지" 파악하기 위한 페이지다.

- 결정일: 2026-05-11
- 결정자: @woohyun212, @SmongsDev, @Pongchi
- 관련 이슈: [#3 — [Infra] 기술 스택 결정](https://github.com/woohyun212/SE-final-project/issues/3) (Closed)
- 관련 ADR: [ADR-0001 (Electron)](./회의록/decisions/0001-electron-as-client-platform.md), [ADR-0002 (Tech Stack)](./회의록/decisions/0002-tech-stack.md)

---

## 한눈에 보기

| 영역 | 채택 | 대안 (탈락) | SRS 연관 |
|---|---|---|---|
| **LLM** | `gemini-3.1-flash-lite-preview` | GPT-4o, Claude Haiku, 로컬 Llama | `ContextAnalyzer`, 추천 이유 |
| **STT** | **어댑터** + Whisper Small (로컬) / Whisper API | Clova, Whisper 단일 백엔드 | `STTService` |
| **음성 감정 ML** | wav2vec2 (fine-tuning) | CNN+멜스펙트로그램, LSTM | `EmotionClassifier`, NFR4.3 |
| **백엔드** | **FastAPI** | Express, Flask | API + ML 동일 런타임 |
| **DB** | **PostgreSQL** | MongoDB | User/Feedback/Recommendation |
| **프론트엔드** | **Electron + Next.js** | React 단독, Vue | `VoiceCapture`, `RecommendationVisualizer` |
| **배포** | **자체 서버** | Heroku, Vercel, Render, AWS, GCP | NFR2.2 (Blue-Green) |
| **네트워크** | **tailscale** | nginx + Let's Encrypt, Cloudflare Tunnel | 운영 접근 |

---

## 항목별 결정 사유 (요약)

> 더 깊은 근거·리스크는 [ADR-0002](./회의록/decisions/0002-tech-stack.md) 의 *Alternatives Considered* / *Consequences* 절 참조.

### LLM — `gemini-3.1-flash-lite-preview`
- 저비용 + 빠른 응답 + 한국어 가용. 학생 프로젝트 비용 통제에 부합.
- ⚠ `preview` 채널 → 모델 ID는 환경변수로 분리, GA 전환 시 별도 ADR.

### STT — 어댑터 패턴 (Whisper Small ↔ Whisper API)
- 핵심은 **어댑터화 자체**. 백엔드 교체로 비용·지연 trade-off 운영 중 조정.
- `STTService` 인터페이스가 두 구현을 가린다. NFR2.3 fallback과 동일 패턴.

### 음성 감정 ML — wav2vec2
- 사전학습 모델이 강력. 캐글 dataset과 fine-tuning 워크플로 친숙.
- 목표: 캐글 테스트셋 정확도 ≥ 70% (NFR4.3).

### 백엔드 — FastAPI
- 비동기 IO + Pydantic + Python ML 스택과 같은 프로세스.
- UC-03의 듀얼 트랙(`EmotionClassifier` ‖ `STTService→ContextAnalyzer`) 병렬 처리에 자연스러움.

### DB — PostgreSQL
- 관계형 안정성 + `JSONB` 로 피드백/추천 이력 같은 반정형 데이터까지 흡수.

### 프론트엔드 — Electron + Next.js
- ADR-0001(Electron) 위에 Next.js를 UI 프레임워크로 확정.
- ⚠ `file://` 프로토콜과 Next.js 라우팅 충돌 가능 — Hello World 배포(#5)에서 선행 검증.

### 배포 — 자체 서버
- API/LLM 비용 통제 + Blue-Green(NFR2.2) 직접 구성 가능 + 학습 가치.
- ⚠ 단일 장애점. 1대 서버 내 컨테이너 이중화로 1차 mitigation.

### 네트워크 — tailscale
- 자체 서버 ↔ 개발자/CI 메시 VPN. SSH/Public IP 노출 최소.
- ⚠ 비상용 SSH 키 1개를 별도 보존.

---

## 후속 작업

| # | 작업 | 트래킹 위치 |
|---|---|---|
| 1 | FastAPI + PostgreSQL 보일러플레이트 | 별도 이슈 (예정) |
| 2 | `STTService` 추상 인터페이스 정의 + 두 어댑터 구현 | Sprint #3 — [US-10](https://github.com/woohyun212/SE-final-project/issues) 에 통합 |
| 3 | tailscale 서버 셋업 | [#5 Hello World 배포](https://github.com/woohyun212/SE-final-project/issues/5) 에 포함 |
| 4 | Electron + Next.js 보일러플레이트 | [#5 Hello World 배포](https://github.com/woohyun212/SE-final-project/issues/5) 에 포함 |
| 5 | SRS v2 작성 시 §7 도메인 어휘에 `STTService` 가 어댑터임을 명시 | SRS v2 PR (예정) |
| 6 | `gemini-*-preview` GA 전환 추적 | 후속 ADR |

---

## 변경 시 규칙

1. 항목 1개라도 바뀌면 **새 ADR을 작성** (ADR-0002를 Superseded 처리).
2. 이 카탈로그(`tech-stack-decision.md`)는 ADR 본문 변경 후 *동기화*만 하는 파생 문서.
3. 코드/스크립트에서 모델 ID·DB URL 등 구체값을 참조할 때는 이 파일이 아니라 환경변수 / `.env.example` 을 SSOT로 사용한다.
