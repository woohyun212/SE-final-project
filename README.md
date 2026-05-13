<div align="center">

# 🎵 AI 기반 감정 분석 음악 추천 시스템

**Voice → Emotion + Context → Music Recommendation**

CWNU 컴퓨터공학과 3학년 1학기 — 소프트웨어 공학 기말 프로젝트

[![Sprint](https://img.shields.io/badge/Sprint-%230%20(W10%E2%86%92W11)-yellow)](./docs/PROJECT_PLAN.md)
[![License](https://img.shields.io/badge/License-MIT-green)](./LICENSE)
[![Stack](https://img.shields.io/badge/Stack-Electron%20%2B%20Next.js%20%2B%20FastAPI-blue)](./docs/tech-stack-decision.md)

</div>

---

## 📖 프로젝트 개요

사용자의 **음성 한 마디**를 듀얼 트랙으로 분석하는 데스크탑 애플리케이션:

```
                 ┌─ ML 트랙:   음성 → 감정 벡터 (wav2vec2)
   🎤 음성 입력 ─┤                              ↘
                 └─ LLM 트랙:  STT → 맥락 (Gemini)     EmotionFusion → 🎵 추천
```

두 트랙의 융합 결과로 Spotify 카탈로그에서 음악을 매칭하고, **감정-음악 2D 매핑 차트** + **LLM 추천 이유**를 함께 제시합니다.

> 자세한 요구사항·설계는 [`docs/회의록/design/srs-v1.md`](./docs/회의록/design/srs-v1.md) 참조.

---

## 🛠 기술 스택

| 영역 | 채택 | 근거 |
|---|---|---|
| 🖥 클라이언트 | Electron + Next.js | [ADR-0001](./docs/회의록/decisions/0001-electron-as-client-platform.md), [ADR-0002](./docs/회의록/decisions/0002-tech-stack.md) |
| 🔧 백엔드 | FastAPI (Python) | ADR-0002 |
| 🧠 ML | wav2vec2 (fine-tuning) | ADR-0002 |
| 💬 LLM | Google Gemini (`flash-lite-preview`) | ADR-0002 |
| 🎙 STT | Whisper (어댑터 — Small 로컬 ↔ API) | ADR-0002 |
| 🗃 DB | PostgreSQL | ADR-0002 |
| ☁ 배포 | 자체 서버 (Blue-Green) | ADR-0002 |
| 🔐 네트워크 | tailscale | ADR-0002 |

→ 한눈 카탈로그: [`docs/tech-stack-decision.md`](./docs/tech-stack-decision.md)

---

## 📁 폴더 구조

```
SE-final-project/
├── docs/                          # 모든 문서 산출물
│   ├── PROJECT_PLAN.md           #   살아있는 진행 문서
│   ├── tech-stack-decision.md    #   기술 스택 카탈로그
│   ├── clarifications.md         #   강의 측 답변 누적
│   ├── interview-mapping.md      #   인터뷰 → FR/NFR 매핑 표
│   ├── ai-interviews/            #   페르소나 + 인터뷰 대화 로그
│   └── 회의록/                    #   설계 단계 SSOT
│       ├── design/               #     SRS + 다이어그램
│       ├── meetings/             #     날짜 기반 회의록
│       └── decisions/            #     ADR (Architecture Decision Records)
├── client/      ⏳ Electron + Next.js (이슈 #5)
├── backend/     ⏳ FastAPI         (이슈 #5)
├── ml/          ⏳ wav2vec2        (Sprint #2 이후)
├── infra/       ⏳ Docker · tailscale · Blue-Green
└── .github/workflows/  ⏳ CI/CD    (이슈 #4)
```

---

## 🚀 시작하기

> ⏳ **현재 Sprint #0 진행 중** — 코드 디렉터리는 [이슈 #5](https://github.com/woohyun212/SE-final-project/issues/5) (Hello World 배포) 완료 시 생성됩니다.
> 실행 방법은 그 시점에 본 섹션에 추가됩니다.

---

## 🤝 협업 컨벤션

### 1. Git Workflow — GitHub Flow + PR 필수

> 💡 **main 에 직접 commit / push 하지 않습니다.** 모든 변경은 feature 브랜치 + PR + 리뷰 + 머지를 거쳐야 합니다.

```
┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────────┐
│  새 브랜치  │ →  │ commit       │ →  │ push + PR    │ →  │ 머지 +     │
│  분기      │    │ (atomic)     │    │ create       │    │ 브랜치 삭제 │
└────────────┘    └──────────────┘    └──────────────┘    └────────────┘
   feature/X        Conventional         gh pr create        gh pr merge
                    Commits              --base main         --merge
```

### 2. 브랜치 명명 규칙

| 종류 | 패턴 | 예시 |
|---|---|---|
| 🆕 기능 | `feature/US-<번호>-<짧은-설명>` | `feature/US-3-voice-recording` |
| 🐛 버그 | `fix/<설명>` | `fix/token-expiry-handler` |
| 📝 문서 | `docs/<설명>` | `docs/adr-0003-redis-cache` |
| 🔧 인프라 | `chore/<설명>` | `chore/gitignore-baseline` |
| ♻️ 리팩터 | `refactor/<설명>` | `refactor/extract-emotion-fusion` |

### 3. 커밋 메시지 — Conventional Commits

```bash
<type>(<scope>): <subject>

<body>            # 필요 시
<footer>          # 이슈 참조 (Refs #N, Closes #N)
```

| Type | 의미 | 예시 |
|---|---|---|
| `feat` | 새 기능 | `feat: US-3 음성 5초 녹음 컴포넌트` |
| `fix` | 버그 수정 | `fix: JWT 만료 시 자동 갱신 처리` |
| `docs` | 문서 변경 | `docs: ADR-0003 Redis 캐시 도입 결정` |
| `chore` | 잡일 (gitignore, 설정) | `chore: ESLint 룰 통일` |
| `test` | 테스트 | `test: EmotionFusion 단위 테스트` |
| `refactor` | 기능 변화 없는 코드 정리 | `refactor: RecommendationEngine 분리` |
| `style` | 포매팅·세미콜론 | — |
| `perf` | 성능 개선 | `perf: 카탈로그 인덱스 추가` |

### 4. Pull Request 규칙

PR 본문에 다음을 포함:

```markdown
## Summary
한두 문장 요약.

## Changes
- 핵심 변경 bullet

## Related
Refs #N  또는  Closes #N

## Test plan
- [ ] 검증 항목 체크리스트
```

**머지 방식**: Merge commit (이 프로젝트의 기본값, [PR #9](https://github.com/woohyun212/SE-final-project/pull/9)부터 정착).
**머지 후**: 헤드 브랜치는 `--delete-branch` 로 즉시 정리.

### 5. Issue 라벨 사용법

| 카테고리 | 라벨 | 용도 |
|---|---|---|
| **Type** | `type/story` · `type/doc` · `type/infra` · `type/bug` | 작업 성격 |
| **Sprint** | `sprint/0` ~ `sprint/5` | 스프린트 분류 |
| **Component** | `comp/client` · `comp/backend` · `comp/ml` · `comp/docs` · `comp/infra` | 영향 영역 |
| **Priority** | `prio/must` · `prio/should` · `prio/could` | MoSCoW 우선순위 |

이슈 생성 시 **Type 1개 + Sprint 1개 + Component 1개 이상 + Priority 1개** 를 기본 조합으로 부여합니다.

### 6. Definition of Done — 모든 코드 PR 공통

- [ ] 단위 테스트 작성 및 통과
- [ ] Lint 통과 (ESLint · Ruff 등)
- [ ] 변경된 라인 커버리지 ≥ 70%
- [ ] 보안: API 키 / 비밀번호 하드코딩 없음 (환경변수 사용)
- [ ] 관련 User Story ID 가 PR 설명에 포함
- [ ] 최소 1명 리뷰 approve
- [ ] 문서 영향이 있다면 관련 markdown 함께 업데이트

### 7. 의사결정의 영속화 — ADR

되돌리기 어렵거나 후임이 "왜 이렇게 했지?" 라고 물을 만한 결정은 **즉시 ADR로 남깁니다**:

- 위치: [`docs/회의록/decisions/`](./docs/회의록/decisions/)
- 번호: `NNNN-짧은-제목.md` (4자리, 직전 ADR + 1)
- 상태: `Proposed` → `Accepted` → 필요 시 `Superseded by NNNN`
- 템플릿: [`docs/회의록/decisions/_template.md`](./docs/회의록/decisions/_template.md)

---

## 📚 문서 인덱스

| 문서 | 위치 |
|---|---|
| 🗺 진행 문서 (Living) | [`docs/PROJECT_PLAN.md`](./docs/PROJECT_PLAN.md) |
| 📋 SRS v1 | [`docs/회의록/design/srs-v1.md`](./docs/회의록/design/srs-v1.md) |
| 🎯 시스템 컨텍스트 다이어그램 | [`docs/회의록/design/diagrams/system-context.svg`](./docs/회의록/design/diagrams/system-context.svg) |
| 🎭 유스케이스 다이어그램 | [`docs/회의록/design/diagrams/usecase.svg`](./docs/회의록/design/diagrams/usecase.svg) |
| 🏛 ADR 목록 | [`docs/회의록/decisions/`](./docs/회의록/decisions/) |
| 🧰 기술 스택 카탈로그 | [`docs/tech-stack-decision.md`](./docs/tech-stack-decision.md) |
| 👥 페르소나 + 인터뷰 | [`docs/ai-interviews/`](./docs/ai-interviews/) |
| 🔗 인터뷰 → FR/NFR 매핑 | [`docs/interview-mapping.md`](./docs/interview-mapping.md) |
| ❓ 명확화 기록 | [`docs/clarifications.md`](./docs/clarifications.md) |
| 📝 회의록 | [`docs/회의록/meetings/`](./docs/회의록/meetings/) |

---

## 👥 Contributors

<table>
  <tr>
    <td align="center" width="33%">
      <a href="https://github.com/woohyun212">
        <img src="https://github.com/woohyun212.png" width="100" alt="w00"/>
      </a>
      <br/>
      <a href="https://github.com/woohyun212"><b>w00</b></a>
      <br/>
      <sub>박우현</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://github.com/SmongsDev">
        <img src="https://github.com/SmongsDev.png" width="100" alt="SmongsDev"/>
      </a>
      <br/>
      <a href="https://github.com/SmongsDev"><b>SmongsDev</b></a>
      <br/>
      <sub>신성민</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://github.com/Pongchi">
        <img src="https://github.com/Pongchi.png" width="100" alt="Pongchi"/>
      </a>
      <br/>
      <a href="https://github.com/Pongchi"><b>Pongchi</b></a>
      <br/>
      <sub>정원준</sub>
    </td>
  </tr>
</table>

---

## 📄 License

MIT License — 자세한 내용은 [`LICENSE`](./LICENSE) 참조.

---

<div align="center">
<sub>Made with 🎶 by CWNU CE @ 2026</sub>
</div>
