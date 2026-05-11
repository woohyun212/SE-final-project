# 회의록 & 설계 허브

> AI 기반 감정 분석 음악 추천 시스템 — 프로젝트 문서의 단일 진실 공급원(SSOT).

---

## 🗺 어디서 무엇을 찾는가

| 찾는 것 | 위치 |
|---|---|
| **무엇을 만드는지** 알고 싶다 | [`design/srs-v1.md`](./design/srs-v1.md) — SRS v1 (요구사항·유스케이스·NFR) |
| **시스템 경계와 외부 의존**을 보고 싶다 | [`design/diagrams/system-context.svg`](./design/diagrams/system-context.svg) |
| **사용자가 어떻게 쓰는지** 보고 싶다 | [`design/diagrams/usecase.svg`](./design/diagrams/usecase.svg) |
| **언제 뭘 정했는지** 추적하고 싶다 | [`decisions/`](./decisions/) — ADR 목록 |
| **이번 주 회의 정리**를 보고 싶다 | [`meetings/2026/`](./meetings/2026/) |
| **새 회의록을 작성**해야 한다 | [`meetings/_template.md`](./meetings/_template.md) 복사 |
| **새 의사결정을 기록**해야 한다 | [`decisions/_template.md`](./decisions/_template.md) 복사 |

---

## 📂 디렉터리 구조

```
회의록/
├── README.md                  ← 지금 이 파일 (네비게이션)
├── AGENTS.md                  ← AI 에이전트용 가이드
│
├── design/                    ← 명세와 다이어그램이 사는 곳
│   ├── srs-v1.md
│   └── diagrams/
│       ├── system-context.svg
│       └── usecase.svg
│
├── meetings/                  ← 회의록 (날짜 기반)
│   ├── _template.md
│   └── 2026/
│       └── 2026-05-11-week1-kickoff.md
│
└── decisions/                 ← Architecture Decision Records (ADR)
    ├── _template.md
    └── 0001-electron-as-client-platform.md
```

---

## ✍️ 기여 규칙

### 회의록을 추가할 때
1. `meetings/_template.md` 를 복사한다.
2. 파일명은 `YYYY-MM-DD-주제.md` 형식. 예) `2026-05-18-week2-arch-review.md`
3. 연도 폴더(`meetings/2026/`)에 넣는다.
4. README의 "최근 회의" 섹션 갱신은 생략 — 디렉터리 자체가 인덱스다.

### 의사결정(ADR)을 기록할 때
- 되돌리기 어렵거나 후임 합류자가 "왜 이렇게 했지?" 라고 물을 만한 결정은 **즉시 ADR로 남긴다**.
- 번호는 `decisions/` 안의 마지막 ADR + 1 (4자리 zero-pad).
- 상태: `Proposed` → `Accepted` → (필요 시) `Superseded by 0042`.

### 설계 명세(`design/`)를 수정할 때
- **버전을 올린다.** `srs-v1.md` 를 크게 바꾸려면 `srs-v2.md` 를 새로 만들고 v1은 보존.
- 이미지 추가는 `design/diagrams/` 하위에 두고 상대 경로 (`./diagrams/...`) 로 참조.
- 컴포넌트 명칭은 SRS §7 도메인 어휘를 그대로 사용 — 다이어그램·코드와 일치시켜야 한다.

---

## 🧭 명명 컨벤션

| 종류 | 규칙 | 예 |
|---|---|---|
| 회의록 | `YYYY-MM-DD-짧은-주제.md` | `2026-05-11-week1-kickoff.md` |
| ADR | `NNNN-짧은-제목.md` (4자리) | `0001-electron-as-client-platform.md` |
| 설계 문서 | `<topic>-v<major>.md` | `srs-v1.md` |
| 다이어그램 | `<topic>.svg` (계층은 폴더로) | `diagrams/system-context.svg` |
| 템플릿/숨김 파일 | `_` 접두사 | `_template.md` |

---

## 🔗 외부 링크

- 강의 안내: [`../26SS-SE-조별과제안내.pdf`](../26SS-SE-조별과제안내.pdf)
- 코드 저장소 루트: [`../`](../)

---

_Last updated: 2026-05-11 · Maintainer: 박우현_
