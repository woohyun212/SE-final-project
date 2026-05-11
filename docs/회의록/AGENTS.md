<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-11 | Updated: 2026-05-11 -->

# 회의록 & Design Hub

## Purpose
프로젝트 문서의 **단일 진실 공급원(SSOT)**. 회의록·설계 명세·다이어그램·의사결정 기록(ADR)이 모두 이 디렉터리에서 관리된다.
설계 변경은 코드보다 **먼저** 이곳에 반영되어야 한다.

> 사람용 네비게이션은 [`README.md`](./README.md). 이 파일은 AI 에이전트가 디렉터리에서 작업할 때의 규칙을 정의한다.

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `design/` | SRS, 명세, 다이어그램. 버전별 보존. |
| `meetings/` | 날짜 기반 회의록 + 템플릿 |
| `decisions/` | Architecture Decision Records (ADR) + 템플릿 |

## Key Files
| File | Description |
|------|-------------|
| `README.md` | 디렉터리 네비게이션 허브 (사람용) |
| `design/srs-v1.md` | **메인 설계 문서 v1** — FR/NFR/UC 전체, 컴포넌트 사전 |
| `design/diagrams/system-context.svg` | 시스템 컨텍스트 다이어그램 |
| `design/diagrams/usecase.svg` | 유스케이스 다이어그램 (UC-01~UC-08) |
| `meetings/_template.md` | 회의록 표준 템플릿 |
| `meetings/2026/2026-05-11-week1-kickoff.md` | 1주차 킥오프 — 주제 결정, 초기 요구사항 |
| `decisions/_template.md` | ADR 표준 템플릿 |
| `decisions/0001-electron-as-client-platform.md` | ADR-0001: Electron 채택 결정 |

## For AI Agents

### Working In This Directory

**🔒 불변 원칙**
- **명명 일관성이 최우선이다.** SRS §7의 컴포넌트 사전 (`VoiceCapture`, `EmotionClassifier`, `STTService`, `ContextAnalyzer`,
  `EmotionFusion`, `RecommendationEngine`, `MusicCatalog`, `FeedbackLogger`, `RecommendationVisualizer`,
  `CatalogSynchronizer`) 의 이름을 SVG/코드/회의록 어디서든 동일하게 사용하라.
- 요구사항 추가/수정 시 **MoSCoW 우선순위(M/S/C)** 와 **추적 가능한 ID** (FR1.x, NFR1.x, UC-0x) 체계를 따르라.
  새 ID는 기존 번호와 충돌하지 않게 부여한다.
- 핵심 유스케이스 **UC-03** 의 P95 ≤ 3초(NFR1.1)는 비기능 기준선 — UC-03 흐름을 바꾸면 관련 다이어그램과
  NFR이 동시에 업데이트되어야 한다.

**📝 새 회의록 작성**
- 위치: `meetings/<YYYY>/`
- 파일명: `YYYY-MM-DD-짧은-주제.md` (예: `2026-05-18-week2-arch-review.md`)
- 시작은 반드시 `meetings/_template.md` 복사로.
- 회의에서 나온 **결정 사항이 ADR감(되돌리기 어려움 + 후임이 이유를 궁금해할 만함)** 이면
  즉시 `decisions/` 에 별도 ADR 파일을 만든다. 회의록에는 ADR 링크만 남긴다.

**🏛 새 ADR 작성**
- 위치: `decisions/`
- 파일명: `NNNN-짧은-제목.md` (4자리 zero-pad, 직전 ADR + 1)
- 상태(Status) 흐름: `Proposed` → `Accepted` → 필요 시 `Superseded by NNNN`.
- ADR을 폐기할 때는 파일을 삭제하지 말고 상태를 `Superseded` / `Deprecated` 로 변경 — **이력을 보존한다.**
- 템플릿: `decisions/_template.md`.

**📐 설계 명세(`design/`) 수정**
- 큰 변경은 **새 버전을 만들어라.** `srs-v1.md` 를 통째로 갈아엎지 말고 `srs-v2.md` 신규 작성.
  v1은 보존(이전 ADR/회의록에서 참조되고 있을 수 있음).
- 새 다이어그램은 `design/diagrams/` 하위에. 상대 경로는 `./diagrams/<file>.svg` 로.
- SVG는 인라인 텍스트 유지, 한글 폰트 스택은 `'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif` 순.
- **캐글 dataset은 외부 시스템으로 그리지 말 것** — 학습 시점에만 사용, 운영 중에는 모델 가중치로 흡수.
- SRS 변경 시 §9 변경 이력 표 갱신과 버전 번호 증가 필수.

**🗂 명명 컨벤션 요약**

| 종류 | 패턴 | 예 |
|---|---|---|
| 회의록 | `YYYY-MM-DD-주제.md` | `2026-05-11-week1-kickoff.md` |
| ADR | `NNNN-주제.md` | `0001-electron-as-client-platform.md` |
| 설계 문서 | `<topic>-v<major>.md` | `srs-v1.md` |
| 다이어그램 | `<topic>.svg` | `diagrams/system-context.svg` |
| 템플릿/숨김 | `_` 접두사 | `_template.md` |

### Testing Requirements

문서 디렉터리이므로 자동화 테스트는 없다. 변경 시 다음을 수동 검증:

| 검증 항목 | 방법 |
|---|---|
| SRS ↔ SVG ID 정합성 | `design/srs-v1.md` 의 컴포넌트명을 SVG에서 grep |
| 외부 시스템 목록 정합성 | SRS §2.2 액터 / §3 외부 인터페이스 / system-context SVG 가 모두 일치하는가 |
| 변경 이력 갱신 | SRS §9 표에 새 버전 행이 추가되었는가 |
| 이미지 상대 경로 | `design/srs-v1.md` 의 `![…](./diagrams/...)` 가 실제 파일을 가리키는가 |
| ADR 번호 충돌 | `ls decisions/` 로 다음 ID 확인 |
| 회의록 → ADR 링크 | 회의록의 "결정 사항"이 ADR 파일로 빠졌는지 |

### Common Patterns
- **표 우선 서술 (Table-first):** 요구사항/액터/외부 인터페이스/컴포넌트는 모두 표로. 산문은 표 상하 1–2줄로 제한.
- **MoSCoW 우선순위:** Must(M) / Should(S) / Could(C).
- **Fallback 명시:** 외부 의존이 있는 시나리오는 대체(A1, A2, …) + 예외(E1, E2, …) 까지 함께 기술.
- **추적성:** 본문에서 다른 항목 참조 시 ID 표기 (예: "NFR1.1", "UC-03 A1") 사용.
- **버전 보존 우선:** 명세는 덮어쓰지 말고 새 버전 파일 생성 — 과거 결정의 컨텍스트를 잃지 않는다.

## Dependencies

### Internal
- `../README.md` — 프로젝트 한 줄 소개
- `../26SS-SE-조별과제안내.pdf` — 강의 측 평가 기준 (요구사항의 상위 제약)

### External (참고)
- [16personalities — Music & Personality 글](https://www.16personalities.com/articles/what-your-music-taste-says-about-your-personality-a-study)
- [Kaggle — Emotion Dataset (Audio)](https://www.kaggle.com/datasets/seungjunlim/emotion-dataset-audio)
- YouTube 감성 플리 (시드 트랙 추출용)

## Current Status
- **SRS:** v1 (2026-05-11)
- **ADR:** 0001 Accepted
- **회의록:** week 1 (2026-05-11 킥오프)

<!-- MANUAL: 이 라인 아래의 수동 주석은 재생성 시에도 보존됩니다. -->
