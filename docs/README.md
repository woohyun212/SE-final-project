# docs

프로젝트 문서의 최상위 컨테이너.

## 카테고리

| 디렉터리 | 내용 |
|---|---|
| [`회의록/`](./회의록/) | 회의록 · SRS · 다이어그램 · ADR — 설계 단계 SSOT |

## 단일 파일 문서

| 파일 | 내용 |
|---|---|
| [`tech-stack-decision.md`](./tech-stack-decision.md) | 현재 기술 스택 카탈로그 (한눈 비교표). 결정 *사유*는 [ADR-0002](./회의록/decisions/0002-tech-stack.md) 가 SSOT. |

## 새 문서 카테고리를 추가할 때
1. `docs/<카테고리명>/` 디렉터리 생성.
2. 그 안에 `README.md` (사람용 인덱스) 와 `AGENTS.md` (AI 규칙) 를 함께 둔다.
3. 위 표에 한 줄 추가.

향후 추가 후보: `runbooks/`, `api/`, `user-guide/`, `onboarding/`, `architecture/`.
