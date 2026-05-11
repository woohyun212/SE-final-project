<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-05-11 | Updated: 2026-05-11 -->

# docs

## Purpose
프로젝트의 **모든 문서**가 모이는 최상위 컨테이너.
현재는 회의록·SRS·ADR 등 설계 단계 산출물이 `회의록/` 하위에 정리되어 있으며,
향후 사용자 가이드·운영 런북·API 문서 등이 추가될 수 있다.

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `회의록/` | 회의록 + SRS + 다이어그램 + ADR (설계 단계 SSOT). 자세한 내부 규칙은 `회의록/AGENTS.md` 와 `회의록/README.md`. |

## Key Files
| File | Description |
|------|-------------|
| `tech-stack-decision.md` | 기술 스택 카탈로그(파생 문서). **이 파일을 수정하지 말고** 먼저 `회의록/decisions/` 의 해당 ADR을 수정한 뒤 동기화한다. 결정 사유의 SSOT는 ADR이다. |

## For AI Agents

### Working In This Directory
- **문서 종류가 늘어나면 새 하위 디렉터리를 만들어라.** 단일 디렉터리에 이질적인 문서를 섞지 말 것.
  예: `docs/runbooks/`, `docs/api/`, `docs/user-guide/`, `docs/onboarding/`.
- 새 카테고리 디렉터리를 추가하면 이 표에도 행을 한 줄 더한다.
- 코드와 직접 결합된 문서(예: 컴포넌트별 README)는 코드 옆에 두고, 여기에는 둘 이상의 컴포넌트를
  가로지르는 문서만 둔다.
- 한글이 들어간 디렉터리(예: `회의록/`)는 셸 명령에서 따옴표로 감쌀 것.

### Common Patterns
- 각 하위 디렉터리는 자체 `README.md` (사람용 네비게이션) 와 `AGENTS.md` (AI용 규칙) 를 가진다.
- 카테고리 간 교차 참조는 절대 경로 대신 저장소 기준 상대 경로로 (`../design/...` 보다 `docs/회의록/design/...` 가 안전).

## Dependencies

### Internal
- 상위 컨텍스트: `../AGENTS.md` (저장소 루트)
- 강의 안내 PDF: `../26SS-SE-조별과제안내.pdf`

<!-- MANUAL: 이 라인 아래의 수동 주석은 재생성 시에도 보존됩니다. -->
