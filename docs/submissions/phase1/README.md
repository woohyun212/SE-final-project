# Phase 1 제출 패키지 (W12 마감)

CWNU 소프트웨어 공학 기말 프로젝트 — AI 기반 감정 분석 음악 추천 시스템 의 1단계 산출물.

- **제출 마감**: 2026년 W12 (`docs/PROJECT_PLAN.md` §6)
- **마일스톤**: [Phase 1: 요구사항·설계 문서 (W12)](https://github.com/woohyun212/SE-final-project/milestone/1)
- **작성**: 박우현(w00), 신성민(SmongsDev), 정원준(Pongchi)
- **빌드 시각**: 2026-05-14

---

## 📄 산출물

| 파일 | 분량 | 원본 HTML | 관련 이슈 |
|---|---|---|---|
| [`01-requirements-document.pdf`](./01-requirements-document.pdf) | 8 pages, 2.0 MB | [`../../01-requirements-document.html`](../../01-requirements-document.html) | [#36](https://github.com/woohyun212/SE-final-project/issues/36) |
| [`02-design-document.pdf`](./02-design-document.pdf) | 8 pages, 1.5 MB | [`../../02-design-document.html`](../../02-design-document.html) | [#37](https://github.com/woohyun212/SE-final-project/issues/37) |

## 📋 포함 내용

### 01 — 요구사항 문서 (Requirements)
- 시스템 개요 / 이해관계자 / 액터
- **페르소나 3명** (김지원·박서준·이수민) — SRS 정당화 근거
- **AI 인터뷰 시뮬레이션 로그 전문** (부록 A) — C-0001 결정에 따른 (a) 페르소나 인터뷰 형식
- 유스케이스 다이어그램 + UC-01~08 명세 (UC-03 핵심 상세)
- 기능 요구사항 FR1~FR7 / 비기능 요구사항 NFR1~NFR6
- 인터뷰 → FR/NFR 매핑 표 (모든 27개 FR 트레이스)
- 명확화 기록 (C-0001) → [`docs/clarifications.md`](../../clarifications.md)

### 02 — 설계 문서 (Design)
- 4+1 뷰 아키텍처 개요 + mermaid flowchart
- 시스템 컨텍스트 다이어그램
- 컴포넌트 사전 (SRS §7 — 10개)
- **클래스 다이어그램** (mermaid classDiagram)
- **시퀀스 다이어그램 UC-03** (mermaid sequenceDiagram + par/alt)
- 데이터 모델 (mermaid erDiagram)
- API 엔드포인트 초안
- ADR-0001 / ADR-0002 색인
- NFR 충족 전략

## 🔧 PDF 생성 방법

두 HTML 문서를 Chrome headless 로 인쇄 변환:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu \
  --no-pdf-header-footer \
  --virtual-time-budget=15000 \
  --print-to-pdf="docs/submissions/phase1/<output>.pdf" \
  "file://$(pwd)/docs/<input>.html"
```

원본 HTML 의 `@page A4` + `@media print` CSS 가 그대로 적용됨. mermaid 다이어그램은 `--virtual-time-budget` 가 충분히 크면 렌더 완료 후 캡처.

## 🔁 갱신 절차

본문 변경이 있으면:
1. `docs/01-requirements-document.html` 또는 `docs/02-design-document.html` 수정
2. 위 명령으로 PDF 재생성
3. 새 PR 으로 본 디렉터리 갱신 — 정책: 별도 브랜치 + reviewer (작성자 제외 팀원)

## 📁 관련 자료 (참조용, PDF 별도 제출 X)

| 자료 | 위치 |
|---|---|
| SRS v1 | [`../../회의록/design/srs-v1.md`](../../회의록/design/srs-v1.md) |
| 페르소나 + 인터뷰 | [`../../ai-interviews/`](../../ai-interviews/) |
| 인터뷰 → FR/NFR 매핑 | [`../../interview-mapping.md`](../../interview-mapping.md) |
| 명확화 기록 | [`../../clarifications.md`](../../clarifications.md) |
| ADR 목록 | [`../../회의록/decisions/`](../../회의록/decisions/) |
| 다이어그램 (SVG) | [`../../회의록/design/diagrams/`](../../회의록/design/diagrams/) |
| 살아있는 진행 문서 | [`../../PROJECT_PLAN.md`](../../PROJECT_PLAN.md) |
