# ADR-0001: 클라이언트 플랫폼으로 Electron 채택

- **상태(Status):** Accepted
- **일자(Date):** 2026-05-11
- **결정자(Deciders):** @woohyun
- **관련 회의록:** [`../meetings/2026/2026-05-11-week1-kickoff.md`](../meetings/2026/2026-05-11-week1-kickoff.md)
- **관련 SRS 항목:** SRS §1 시스템 개요 / NFR6.1 이식성 / FR2 음성 입력

---

## Context

본 프로젝트는 사용자의 **마이크 음성 입력**을 받아 ML/LLM으로 분석하고 추천을 시각화하는
인터랙티브 애플리케이션이다. 다음 제약을 동시에 만족해야 했다:

1. **이식성:** Windows 10+, macOS 12+, Ubuntu 22+ 모두 지원 (NFR6.1).
2. **로컬 자원 접근:** 마이크 권한 / 파일 시스템 / OS 알림 등 네이티브 API 필요.
3. **개발 일정:** 학기말 프로젝트 4–6주 (SRS §8 제약사항). 세 플랫폼 각각에 네이티브 코드를
   짤 인력이 없다.
4. **시각화 복잡도:** 감정-음악 2D 매핑 차트 + LLM 텍스트 + 곡 리스트 (FR5). 웹 기반
   차트 라이브러리 생태계를 활용하면 빠르다.
5. **팀의 기존 역량:** 팀 구성원의 주력 스택이 웹(JS/TS) 쪽에 가깝다.

## Decision

**클라이언트는 Electron 으로 구현한다.**

- 단일 코드베이스로 Windows / macOS / Linux 모두 지원 → NFR6.1 충족.
- `MediaRecorder` API 로 마이크 녹음 (FR2.1) — 별도 네이티브 바인딩 불필요.
- 웹 기반 차트 라이브러리(예: D3, Chart.js, Plotly) 활용 가능 → FR5.1 빠른 구현.
- 팀의 JS/TS 역량을 그대로 적용 — 학습 비용 최소.

## Alternatives Considered

| 선택지 | 장점 | 단점 | 채택 여부 |
|---|---|---|---|
| **A. Electron** | 크로스플랫폼 단일 코드 / 웹 생태계 / 마이크 API 표준화 | 메모리/번들 크기 큼 | ✅ |
| **B. 웹 (PWA)** | 설치 불필요 / 더 가벼움 | 데스크탑 OS 알림·트레이 통합 약함 / 마이크 권한 모델이 브라우저별로 상이 | ❌ |
| **C. 플랫폼별 네이티브 (Swift + WinUI + GTK)** | 최고 성능 / 작은 바이너리 | 4–6주 안에 3-플랫폼 구현은 비현실적 | ❌ |
| **D. Flutter Desktop** | 단일 코드 + 네이티브 성능 | Dart 학습 비용 / 오디오 녹음 패키지 성숙도 낮음 | ❌ |
| **E. Tauri** | 가벼움 / Rust 보안 모델 | Rust 학습 비용 / 팀 역량 미흡 | ❌ |

## Consequences

### 긍정적
- 백엔드(Python/ML)와 클라이언트를 분리 운영 가능 → SRS §7 컴포넌트 위치 구분이 자연스럽다.
- HTML/CSS/JS 기반이라 디자인 변경이 빠르다.
- 빌드/배포 파이프라인이 잘 갖춰진 도구(electron-builder 등) 활용 가능.

### 부정적 / 리스크
- 메모리 사용량(≈150–300MB)이 크다 — 저사양 환경에서 체감 차이 가능.
- 보안: Electron 의 Node 통합 노출 위험 → `contextIsolation: true`, `nodeIntegration: false` 강제 필요.
- 코드 사이닝(특히 macOS notarization) 절차가 추가 작업.

### 후속 조치
- [ ] Electron + TypeScript 보일러플레이트 셋업
- [ ] `contextIsolation` / CSP 보안 가이드를 별도 ADR로 정리
- [ ] CI에서 3-플랫폼 빌드 매트릭스 구성

---

## 참고 자료
- Electron Security: <https://www.electronjs.org/docs/latest/tutorial/security>
- SRS v1 §1 시스템 개요, §5 NFR6
