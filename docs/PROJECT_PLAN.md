# PROJECT PLAN — AI 기반 감정 분석 음악 추천 시스템

> **이 문서의 목적**: LLM 코딩 에이전트(Claude Code, Cursor, Aider 등)가 작업을 수행할 때 참조하는 단일 컨텍스트 문서.
> **유지 정책**: 살아있는 문서(living document). 매 sprint 종료 시 [현재 상태], [완료 목록], [다음 sprint] 섹션 업데이트.
> **현재 시점**: 2026년 1학기, Week 10 → Week 11 경계.
> **마지막 갱신**: 2026-05-12

---

## 1. 프로젝트 개요

소프트웨어공학 강의 학기말 프로젝트. AI 도구를 활용한 애자일(Scrum-lite) 방식 개발.

**제품 한 줄 설명**: 사용자의 음성을 듀얼 트랙(ML 감정분류 + LLM 맥락분석)으로 분석하여 Spotify 카탈로그에서 음악을 추천하는 Electron 데스크탑 앱.

### 핵심 기능
- 음성 입력 (Electron MediaRecorder)
- ML 기반 음성 감정 분류 (캐글 dataset 학습 모델)
- STT + LLM 기반 맥락 분석
- 감정+맥락 융합 → Spotify audio features 유사도 매칭
- 추천 결과: 곡 리스트 + 감정-음악 2D 매핑 차트 + LLM 추천 이유 설명
- 좋아요/싫어요/재생 피드백 → 개인화

### 시스템 경계 (외부 의존성)
- Spotify Web API (메인 매칭 엔진)
- LLM API (맥락 분석, 추천 이유 생성) — provider 미정
- YouTube Data API (감성 플레이리스트에서 시드 트랙 추출)
- 캐글 emotion-dataset-audio (개발/학습 시점에만, 운영 시 모델로 흡수됨)

---

## 2. 시스템 컴포넌트 (도메인 어휘)

**후속 코드/다이어그램에서 일관되게 사용할 이름.**

| 컴포넌트 | 위치 | 책임 |
|---|---|---|
| `VoiceCapture` | Client (Electron) | MediaRecorder로 음성 녹음 및 전송 |
| `EmotionClassifier` | ML Server | 캐글 학습 모델, 음성 → 감정 벡터 |
| `STTService` | Backend | 음성 → 텍스트 변환 |
| `ContextAnalyzer` | Backend (LLM API 호출) | 텍스트 → 맥락 표현 추출 |
| `EmotionFusion` | Backend | 감정 벡터 + 맥락 표현 융합 |
| `RecommendationEngine` | Backend | Spotify audio features 기반 유사도 매칭 |
| `MusicCatalog` | Backend (DB) | Spotify + YouTube 시드로 구축된 곡 풀 |
| `FeedbackLogger` | Backend | 좋아요/싫어요/재생률 기록 |
| `RecommendationVisualizer` | Client | 2D 차트 + LLM 이유 설명 렌더링 |
| `CatalogSynchronizer` | Backend (Scheduler) | YouTube 플리 → Spotify 매칭 → 카탈로그 적재 |

---

## 3. 기술 스택

> 모든 항목 확정. 결정 사유 SSOT는 [ADR-0002](./회의록/decisions/0002-tech-stack.md), 카탈로그는 [`tech-stack-decision.md`](./tech-stack-decision.md).

| 영역 | 결정 | 비고 |
|---|---|---|
| 클라이언트 | **Electron + Next.js** | ADR-0001 (Electron) + ADR-0002 (Next.js) |
| 백엔드 | **FastAPI** (Python) | ADR-0002 — 백엔드와 ML이 같은 Python 런타임 |
| ML 모델 서빙 | **wav2vec2** (fine-tuning, Python) | ADR-0002 — 캐글 dataset으로 학습 |
| 데이터베이스 | **PostgreSQL** | ADR-0002 — `JSONB` 로 반정형 데이터 흡수 |
| 캐시 | Redis (선택) | 추천 결과 캐싱용 (FR4.4) |
| LLM Provider | **Google Gemini** (`gemini-3.1-flash-lite-preview`) | ADR-0002 — preview 채널, 모델 ID는 env로 분리 |
| STT | **Whisper** (어댑터: `STTService`) — Whisper Small (로컬) ↔ Whisper API | ADR-0002 — 백엔드 런타임 전환 가능 |
| 배포 | **자체 서버** (Blue-Green 구성) | ADR-0002 — API/LLM 비용 통제 + NFR2.2 |
| 네트워크 | **tailscale** (메시 VPN) | ADR-0002 — 자체 서버 ↔ 개발자/CI 접근 |
| 버전 관리 | GitHub | 라벨 19개 + 마일스톤 3개 + Sprint #0 이슈 7개 생성됨 (#2~#8) |
| CI/CD | GitHub Actions | 자동 테스트 + 빌드 + 배포 (이슈 #4 진행 예정) |

---

## 4. 요구사항 요약

### 기능 요구사항 (FR) — Must 우선순위만
- **FR1**: 사용자 계정 (회원가입/로그인/탈퇴)
- **FR2**: 음성 입력 (마이크 권한, 60초 제한, TLS 전송)
- **FR3**: 듀얼 트랙 분석 (EmotionClassifier + STT + ContextAnalyzer + EmotionFusion)
- **FR4**: 음악 추천 (유사도 매칭, 상위 K=10, LLM 추천 이유)
- **FR5**: 시각화 (2D 매핑 차트, 곡 리스트, 추천 이유, 재생)
- **FR6**: 피드백 (좋아요/싫어요, 재생 이벤트 로깅, 개인화 반영)
- **FR7**: 카탈로그 관리 (YouTube 시드 → Spotify 매칭 → 적재)

> 상세는 [`회의록/design/srs-v1.md`](./회의록/design/srs-v1.md) §4 참조.

### 비기능 요구사항 (NFR) — Definition of Done에 흡수
- **성능**: 음성 → 추천 응답 ≤ 3초 (P95), ML 추론 ≤ 1.5초
- **가용성**: 99% 이상, Blue-Green 배포 (다운타임 0), LLM/ML 장애 시 fallback
- **보안**: TLS 1.2+, 음성 원본 분석 후 즉시 폐기, bcrypt(cost≥12), API 키 환경변수
- **품질**: 추천 좋아요율 ≥ 50%, Precision@10 ≥ 0.4, ML 정확도 ≥ 70%, 테스트 커버리지 ≥ 70%
- **사용성**: 첫 추천까지 ≤ 3 클릭, 색맹 대응 팔레트
- **이식성**: Windows 10+/macOS 12+/Ubuntu 22+ (Electron)

---

## 5. 현재 상태 (Week 10 종료 시점)

### ✅ 완료
- [x] 요구사항 fuzzy 결정 정리 (음악 출처/입력 방식/클라이언트/시각화/평가 지표)
- [x] SRS v1 작성 ([`회의록/design/srs-v1.md`](./회의록/design/srs-v1.md)) — 작성자: 박우현
- [x] 시스템 컨텍스트 다이어그램 ([`회의록/design/diagrams/system-context.svg`](./회의록/design/diagrams/system-context.svg))
- [x] 유스케이스 다이어그램 ([`회의록/design/diagrams/usecase.svg`](./회의록/design/diagrams/usecase.svg))
- [x] UC-03(핵심 유스케이스) 상세 명세
- [x] 도메인 어휘 사전 정의
- [x] **ADR-0001** Electron 클라이언트 채택 ([`회의록/decisions/0001-...`](./회의록/decisions/0001-electron-as-client-platform.md))
- [x] **ADR-0002** 기술 스택 8개 영역 확정 ([`회의록/decisions/0002-tech-stack.md`](./회의록/decisions/0002-tech-stack.md)) — 이슈 #3 Closed
- [x] 기술 스택 카탈로그 ([`tech-stack-decision.md`](./tech-stack-decision.md))
- [x] **GitHub 백로그 인프라**: 라벨 19개 + 마일스톤 3개 (Phase 1/2/3) + Sprint #0 이슈 7개 (#2~#8) 생성
- [x] 문서 구조 개편: `docs/회의록/{design,meetings,decisions}` 계층 도입

### 🟡 진행 중 / Sprint #0 잔여
- [ ] (긴급) TA/교수에 "AI 시뮬레이션 로그" 정의 확인 — 이슈 [#8](https://github.com/woohyun212/SE-final-project/issues/8)
- [ ] 사용자 페르소나 2-3명 — 이슈 [#6](https://github.com/woohyun212/SE-final-project/issues/6)
- [ ] AI 인터뷰 시뮬레이션 로그 — 이슈 [#7](https://github.com/woohyun212/SE-final-project/issues/7) (#8 답변 후)
- [ ] GitHub repo 폴더 구조 + README — 이슈 [#2](https://github.com/woohyun212/SE-final-project/issues/2)
- [ ] CI 파이프라인 (lint + test) — 이슈 [#4](https://github.com/woohyun212/SE-final-project/issues/4)
- [ ] Hello World 배포 (자체 서버 + tailscale + Electron+Next.js 검증) — 이슈 [#5](https://github.com/woohyun212/SE-final-project/issues/5)

### ❌ 미착수 (Sprint #1+)
- [ ] 클래스 다이어그램 (Sprint #1)
- [ ] 시퀀스 다이어그램 UC-03 (Sprint #1)
- [ ] 아키텍처 개요 4+1 뷰 (Sprint #1)
- [ ] User Story 코드 (US-1 ~ US-22)

---

## 6. 학기 일정 (W10 → W16, 6주)

각 sprint는 **문서 트랙 + 코드 트랙 병행**.

### Week 10 (현재) — Sprint #0: 환경 + 페르소나
**Sprint Goal**: 코드 작성을 위한 기반 마련 + 1단계 문서 보강.

**문서 트랙 Tasks**
- [ ] 페르소나 2–3명 작성 (이름/나이/직업/음악 청취 맥락/페인 포인트)
- [ ] AI 인터뷰 시뮬레이션 로그 (페르소나마다 1회씩, 채팅 형태 기록)
- [ ] 인터뷰 결과 → FR/NFR 매핑 표 작성
- [ ] 교수/TA에 "AI 시뮬레이션 로그" 정의 확인

**코드 트랙 Tasks**
- [ ] GitHub repo 생성 + `/docs` `/client` `/backend` `/ml` 폴더 구조
- [ ] `README.md` 작성 (실행 방법, 기여 가이드)
- [ ] GitHub Projects 보드 세팅
- [ ] 기술 스택 결정 회의 (LLM, STT, 백엔드 FW, DB)
- [ ] CI 파이프라인 (Actions): lint + test 자동 실행
- [ ] "Hello World" 스켈레톤 코드 배포 (Heroku/Vercel/Render)

**Definition of Done**
- repo가 public 또는 팀원 접근 가능
- `git clone` 후 README대로 따라가면 로컬 실행 가능
- 페르소나 + 인터뷰 로그가 markdown으로 정리됨

---

### Week 11 — Sprint #1: 얇은 Vertical Slice
**Sprint Goal**: End-to-end 동작 (더미 데이터로). 화면 → 백엔드 → 응답 사이클 검증.

**문서 트랙 Tasks**
- [ ] 클래스 다이어그램 (10개 컴포넌트 + 도메인 엔티티)
- [ ] 시퀀스 다이어그램 (UC-03 주 시나리오, par frame으로 듀얼 트랙 표현)
- [ ] 아키텍처 개요 (4+1 뷰: Logical + Deployment 우선)

**코드 트랙 Tasks (User Stories)**
- [ ] **US-1**: As a 사용자, I want 이메일로 회원가입을 하고 싶다
- [ ] **US-2**: As a 사용자, I want 로그인/로그아웃을 할 수 있다
- [ ] **US-3**: As a 사용자, I want 메인 화면에서 음성을 5초 녹음할 수 있다
- [ ] **US-4**: 녹음 종료 시 백엔드가 **하드코딩 더미 추천 5곡**을 반환한다
- [ ] **US-5**: 화면에 추천 곡 리스트가 표시된다 (앨범 아트 placeholder)

**Definition of Done**
- 위 5개 스토리 통과 단위 테스트 작성
- 응답 시간 측정 인프라 구축 (P95 측정 가능)
- 클래스/시퀀스 다이어그램 PR로 머지

---

### Week 12 — Sprint #2: ML + Spotify 실제 연동 ★ 1단계 제출
**Sprint Goal**: 진짜 음성 감정 분류 + 진짜 Spotify 추천. 1단계 문서 두 개 제출.

**문서 트랙 Tasks**
- [ ] 요구사항 문서 통합 정리 (SRS + 페르소나 + 인터뷰 로그 + 시뮬레이션 로그 → 10–15p)
- [ ] 설계 문서 통합 정리 (시스템 컨텍스트 + 유스케이스 + 클래스 + 시퀀스 + 아키텍처 → 5–10p)
- [ ] 🎯 **W12 마감: 1단계 제출**

**코드 트랙 Tasks**
- [ ] **US-6**: 음성에서 감정 벡터를 추출하는 ML 서비스 (EmotionClassifier)
- [ ] **US-7**: Spotify Web API 연동 (audio features 조회)
- [ ] **US-8**: 감정 벡터 → Spotify 카탈로그에서 유사도 매칭 (RecommendationEngine)
- [ ] **US-9**: 카탈로그 시드 데이터 적재 (CatalogSynchronizer, YouTube 플리 → Spotify 매칭)

**Definition of Done**
- 더미 추천 코드가 실제 추천으로 교체됨
- ML 모델 평가: 캐글 테스트셋에서 정확도 측정 (목표 70%)
- 통합 테스트: 음성 입력 → 실제 곡 응답까지의 e2e 테스트 통과

---

### Week 13 — Sprint #3: LLM 맥락 분석
**Sprint Goal**: 듀얼 트랙 완성. 음성 감정 + 텍스트 맥락 둘 다 반영된 추천.

**코드 트랙 Tasks**
- [ ] **US-10**: STT 연동 (STTService)
- [ ] **US-11**: LLM 맥락 분석 (ContextAnalyzer)
- [ ] **US-12**: 감정 + 맥락 융합 (EmotionFusion)
- [ ] **US-13**: 각 추천 곡에 LLM 추천 이유 첨부 (FR4.3)
- [ ] **US-14**: Fallback 처리 (LLM 장애 시 룰베이스, ML 장애 시 텍스트만)

**Definition of Done**
- 듀얼 트랙 병렬 호출 구현 (NFR1.1 ≤ 3초 충족 위해 필수)
- LLM 프롬프트 템플릿 버전 관리 (`prompts/` 폴더)
- Fallback 분기 단위 테스트 통과

---

### Week 14 — Sprint #4: 시각화 + 피드백
**Sprint Goal**: 사용자가 실제로 쓸 만한 수준의 UI/UX 완성.

**코드 트랙 Tasks**
- [ ] **US-15**: 감정-음악 2D 매핑 차트 (valence × energy 평면)
- [ ] **US-16**: 추천 이유 텍스트 카드 UI
- [ ] **US-17**: 좋아요/싫어요 버튼 + 백엔드 기록
- [ ] **US-18**: 재생 이벤트 로깅 (시작/종료/완료)
- [ ] **US-19**: 누적 피드백을 추천 시 가중치로 반영
- [ ] **US-20**: 추천 이력 조회 화면

**Definition of Done**
- 차트가 색맹 대응 팔레트 사용 (NFR5.2)
- 피드백이 즉시 다음 추천에 반영되는지 통합 테스트
- 사용성 셀프 체크: 첫 추천까지 ≤ 3 클릭 (NFR5.1)

---

### Week 15 — Sprint #5: 마무리 + 배포 ★ 테스트 보고서 제출
**Sprint Goal**: Blue-Green 배포 시연 + 테스트 정리.

**문서 트랙 Tasks**
- [ ] 테스트 보고서 작성 (5–10p)
  - 단위/통합 테스트 케이스 목록
  - 커버리지 결과 (Jest/Pytest 출력)
  - 발견한 버그 로그 + 수정 PR 링크
  - AI로 생성한 테스트 스크립트 사례
- [ ] 🎯 **W15 말 마감: 테스트 보고서 제출**

**코드 트랙 Tasks**
- [ ] **US-21**: Blue-Green 배포 구성 (Docker Compose + nginx 또는 플랫폼 기본 기능)
- [ ] **US-22**: 무중단 업데이트 시연 시나리오 작성
- [ ] 버그 수정 + 성능 튜닝 (P95 ≤ 3초 확인)
- [ ] 테스트 커버리지 70% 달성

**Definition of Done**
- 배포된 시스템이 외부에서 접근 가능
- "blue → green 트래픽 전환 → 다시 blue" 시연이 1분 이내에 가능
- 커버리지 리포트가 70% 이상

---

### Week 16 — 최종 마무리 ★ 최종 제출
**Sprint Goal**: 발표 + 데모 영상 + 최종 보고서.

**Tasks**
- [ ] 데모 영상 촬영 (5–10분, 스토리: 페르소나 → 음성 입력 → 추천 → 피드백 → Blue-Green 시연)
- [ ] 최종 보고서 통합 (20–30p)
  - 1단계 요구사항 문서 + 설계 문서
  - 2단계 테스트 보고서
  - 전체 프로세스 요약 (sprint별 회고록 누적분 활용)
  - **AI 활용 분석 (장단점 논의)** ← 매 sprint 회고록 활용
- [ ] 발표 자료 (10–15 슬라이드 + 데모 스크립트)
- [ ] 🎯 **W16 최종 제출**

---

## 7. Definition of Done — 모든 코드 PR 공통

PR이 머지되려면 다음을 모두 만족:

- [ ] 단위 테스트 작성 및 통과
- [ ] Lint 통과 (ESLint/Ruff 등)
- [ ] 변경된 라인 커버리지 ≥ 70%
- [ ] 응답 시간 영향 측정 (해당 시)
- [ ] PR 설명에 관련 User Story ID 명시
- [ ] 최소 1명 리뷰 approve
- [ ] 보안: API 키/비밀번호 하드코딩 없음 (환경변수 사용)
- [ ] 문서 영향이 있다면 관련 markdown 함께 업데이트

---

## 8. 개발 컨벤션

### Git Workflow
- **브랜치 전략**: GitHub Flow (main + feature branch)
- **브랜치명**: `feature/US-<번호>-<짧은-설명>`, `fix/<설명>`, `docs/<설명>`
- **커밋 메시지**: Conventional Commits
  - `feat: US-3 음성 녹음 컴포넌트 구현`
  - `fix: 토큰 만료 시 자동 갱신 처리`
  - `docs: 클래스 다이어그램 추가`
  - `test: EmotionFusion 단위 테스트`
- **PR 머지 후 브랜치 삭제**

### 폴더 구조 (현재 + 예정)
```
/
├── docs/                          # 모든 산출물
│   ├── README.md                  # 카테고리 인덱스
│   ├── AGENTS.md                  # AI 에이전트 가이드
│   ├── PROJECT_PLAN.md            # 이 파일 (살아있는 문서)
│   ├── tech-stack-decision.md     # 기술 스택 카탈로그 (ADR-0002 파생)
│   └── 회의록/                     # 설계 단계 SSOT
│       ├── README.md              # 네비게이션 허브
│       ├── AGENTS.md
│       ├── design/
│       │   ├── srs-v1.md
│       │   └── diagrams/
│       │       ├── system-context.svg
│       │       └── usecase.svg
│       ├── meetings/
│       │   ├── _template.md
│       │   └── 2026/
│       │       └── 2026-05-11-week1-kickoff.md
│       └── decisions/             # ADR (Architecture Decision Records)
│           ├── _template.md
│           ├── 0001-electron-as-client-platform.md
│           └── 0002-tech-stack.md
├── client/                        # ⏳ Electron + Next.js (이슈 #5)
│   ├── src/
│   └── tests/
├── backend/                       # ⏳ FastAPI (이슈 #5)
│   ├── src/
│   ├── tests/
│   └── prompts/                   # LLM 프롬프트 템플릿
├── ml/                            # ⏳ wav2vec2 학습/서빙
│   ├── train/
│   ├── serve/
│   └── tests/
├── infra/                         # ⏳ 자체 서버 + tailscale + Blue-Green (Docker)
└── .github/workflows/             # ⏳ CI/CD (이슈 #4)
```

### 환경 변수 (예시)
```
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
LLM_API_KEY=
LLM_PROVIDER=        # openai | anthropic | google
STT_PROVIDER=        # whisper-api | whisper-local | clova
YOUTUBE_API_KEY=
DATABASE_URL=
REDIS_URL=
JWT_SECRET=
```

---

## 9. 평가 지표 추적 (NFR4 충족용)

매 sprint 종료 시 측정 및 기록:

| 지표 | 목표 | 측정 방법 |
|---|---|---|
| 응답 시간 P95 | ≤ 3초 | 부하 테스트 (k6 또는 locust) |
| ML 모델 정확도 | ≥ 70% | 캐글 테스트셋 |
| 추천 좋아요율 | ≥ 50% | 베타 사용자 피드백 누적 |
| Precision@10 | ≥ 0.4 | 추천된 상위 10개 중 좋아요 비율 |
| 테스트 커버리지 | ≥ 70% | Jest/Pytest coverage 리포트 |

---

## 10. 즉시 다음 액션 (W10 → W11 전환)

이슈 번호 기준. 의존성 순서:

1. **이슈 [#8](https://github.com/woohyun212/SE-final-project/issues/8)** — TA/교수에 "AI 시뮬레이션 로그" 정의 확인 ← 가장 시급, #7을 블로킹
2. **이슈 [#6](https://github.com/woohyun212/SE-final-project/issues/6)** — 페르소나 2–3명 초안 작성 (병렬 가능)
3. **이슈 [#2](https://github.com/woohyun212/SE-final-project/issues/2)** — repo 폴더 구조 + README (병렬 가능)
4. **이슈 [#4](https://github.com/woohyun212/SE-final-project/issues/4)** — CI 파이프라인 (#2 이후)
5. **이슈 [#5](https://github.com/woohyun212/SE-final-project/issues/5)** — Hello World 배포 + 자체 서버 + tailscale + Electron+Next.js 검증 (#2 이후)
6. **이슈 [#7](https://github.com/woohyun212/SE-final-project/issues/7)** — AI 인터뷰 시뮬레이션 (#8 답변 후)
7. **W10 회고 + Sprint #1 백로그 픽** — 위 6개가 끝나면

> 이미 끝난 작업(기술 스택 결정 = 이슈 #3, 회의록/decisions 체계 도입)은 §5 완료 섹션 참조.

---

## 11. 산출물 인덱스

### 설계/의사결정 (현재 위치 기준)
| 파일 | 위치 | 상태 |
|---|---|---|
| SRS v1 | `docs/회의록/design/srs-v1.md` | ✅ 작성 완료 |
| 시스템 컨텍스트 다이어그램 | `docs/회의록/design/diagrams/system-context.svg` | ✅ 작성 완료 |
| 유스케이스 다이어그램 | `docs/회의록/design/diagrams/usecase.svg` | ✅ 작성 완료 |
| ADR-0001 (Electron 채택) | `docs/회의록/decisions/0001-electron-as-client-platform.md` | ✅ Accepted |
| ADR-0002 (기술 스택 확정) | `docs/회의록/decisions/0002-tech-stack.md` | ✅ Accepted |
| 기술 스택 카탈로그 | `docs/tech-stack-decision.md` | ✅ 작성 완료 |
| Week 1 킥오프 회의록 | `docs/회의록/meetings/2026/2026-05-11-week1-kickoff.md` | ✅ |

### Sprint #0 진행 중
| 파일 | 위치 | 상태 |
|---|---|---|
| 페르소나 문서 | `docs/personas.md` (예정) | ⬜ 이슈 #6 |
| AI 인터뷰 시뮬레이션 로그 | `docs/ai-interviews/` (예정) | ⬜ 이슈 #7 |
| 인터뷰 ↔ FR/NFR 매핑 표 | `docs/interview-mapping.md` (예정) | ⬜ 이슈 #7 |
| Clarification 기록 | `docs/clarifications.md` (예정) | ⬜ 이슈 #8 |

### Sprint #1+ 예정
| 파일 | 위치 (예정) | 상태 |
|---|---|---|
| 클래스 다이어그램 | `docs/회의록/design/diagrams/class.svg` | ⬜ Sprint #1 |
| 시퀀스 다이어그램 (UC-03) | `docs/회의록/design/diagrams/sequence-uc03.svg` | ⬜ Sprint #1 |
| 아키텍처 개요 | `docs/architecture-overview.md` | ⬜ Sprint #1 |
| 1단계 통합 요구사항 문서 | `docs/01-requirements-document.md` | ⬜ Sprint #2 (W12 제출) |
| 1단계 통합 설계 문서 | `docs/02-design-document.md` | ⬜ Sprint #2 (W12 제출) |
| 테스트 보고서 | `docs/03-test-report.md` | ⬜ Sprint #5 (W15 제출) |
| 최종 보고서 | `docs/04-final-report.md` | ⬜ Week 16 |
| 발표 자료 | `docs/presentation.pdf` | ⬜ Week 16 |
| 데모 영상 | `docs/demo-video.mp4` | ⬜ Week 16 |

---

## 변경 이력

| 버전 | 일자 | 변경 사항 |
|---|---|---|
| v1.0 | 2026-05-11 | 초안 작성 (W10 시점) |
| v1.1 | 2026-05-12 | Sprint #0 진척 반영: ADR-0001/0002 채택, 기술 스택 8개 영역 확정, GitHub 백로그 인프라(라벨 19+마일스톤 3+이슈 #2~#8) 생성, `docs/회의록/{design,meetings,decisions}` 구조 도입, 산출물 인덱스 경로 갱신 |
