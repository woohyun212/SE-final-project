# ADR-0002: 초기 기술 스택 확정 (LLM · STT · ML · 백엔드 · DB · 프론트엔드 · 배포 · 네트워크)

- **상태(Status):** Accepted
- **일자(Date):** 2026-05-11
- **결정자(Deciders):** @woohyun212, @SmongsDev, @Pongchi
- **관련 회의록:** [`../meetings/2026/2026-05-11-week1-kickoff.md`](../meetings/2026/2026-05-11-week1-kickoff.md)
- **관련 이슈:** [#3 — [Infra] 기술 스택 결정](https://github.com/woohyun212/SE-final-project/issues/3)
- **관련 ADR:** [ADR-0001 (Electron 채택)](./0001-electron-as-client-platform.md) 의 후속 보강
- **관련 SRS 항목:** SRS §3 외부 인터페이스 / §5 NFR1 (성능) / §7 도메인 어휘

---

## Context

SRS v1은 컴포넌트 책임은 정의했으나 구체 기술은 TBD 상태였다. 이슈 #3은 7가지 결정 항목을
잡았고, 회의 중 **네트워크 관리** 한 항목이 추가로 발견되어 총 8개를 확정했다.

핵심 제약:
- **기간:** 학기말 4–6주 (SRS §8) — 학습 곡선이 큰 스택은 배제.
- **예산:** 학생 프로젝트 — API 호출 비용을 최대한 통제해야 한다.
- **운영 자율성:** 데모/시연을 외부 종속 없이 통제 가능해야 한다.
- **언어:** 한국어 STT 품질이 가용해야 한다.
- **팀 역량:** JS/TS + Python 양쪽 친숙.
- **컴포넌트:** SRS §7의 `STTService`, `ContextAnalyzer`, `EmotionClassifier`, `RecommendationEngine`, `VoiceCapture`, `MusicCatalog` 와 정합해야 한다.

## Decision

다음 8개 기술을 채택한다.

| 영역 | 결정 | 핵심 이유 |
|---|---|---|
| **LLM** | `gemini-3.1-flash-lite-preview` | 저비용 + 빠른 응답 + 한국어 가용 — `ContextAnalyzer` / 추천 이유 생성에 충분한 품질. |
| **STT** | **어댑터 패턴** + `Whisper Small (로컬)` ↔ `Whisper API` 양 백엔드 | 운영 중 비용·지연 trade-off에 따라 백엔드 교체 가능. `STTService` 인터페이스로 캡슐화. |
| **음성 감정 ML baseline** | `wav2vec2` | 사전학습 모델이 강력하고 캐글 dataset과 fine-tuning 워크플로 친숙. `EmotionClassifier`. |
| **백엔드 프레임워크** | **FastAPI** | 비동기 IO + Pydantic + Python ML 스택과 같은 프로세스. UC-03 듀얼 트랙 병렬 처리에 유리. |
| **데이터베이스** | **PostgreSQL** | 관계형 안정성 + `JSONB`로 피드백/추천 이력 같은 반정형 데이터까지 흡수. |
| **프론트엔드** | **Electron + Next.js** | ADR-0001(Electron) 위에 Next.js UI 프레임워크 확정. 라우팅·컴포넌트 생태계 활용. |
| **배포 플랫폼** | **자체 서버** | API/LLM 비용 통제 + Blue-Green(NFR2.2) 직접 구성 가능 + 학습 가치. |
| **네트워크 관리** | **tailscale** | 자체 서버 ↔ 개발자/CI 메시 VPN. 별도 ingress·SSH·Let's Encrypt 셋업 최소화. |

## Alternatives Considered

| 영역 | 대안 | 탈락 이유 |
|---|---|---|
| LLM | OpenAI GPT-4o | 비용 ↑, flash-lite로 충분 |
| LLM | Claude Haiku | Gemini 대비 한국어 미세 열세 (체감) |
| LLM | 로컬 LLM (Llama 등) | GPU 부담 |
| STT | Clova (Naver) | 벤더 종속 + 가격 정책 변동 리스크 |
| STT | Whisper만 (어댑터 X) | 장애 시 fallback 부재 (NFR2.3 위배 가능) |
| ML | CNN+멜스펙트로그램 | wav2vec2 대비 정확도 낮음 |
| ML | LSTM | 학습 시간 ↑ |
| Backend | Express | Python ML과 IPC 추가 필요 |
| Backend | Flask | 비동기 성능 ↓ |
| DB | MongoDB | 관계형 모델(User-Feedback-Music)에 부적합 |
| Frontend | React 단독 | 라우팅/SSR 추가 작업 필요 |
| Frontend | Vue | 팀 친숙도 ↓ |
| Deploy | Heroku/Vercel/Render | 음성 처리 비용 ↑, cold start |
| Deploy | AWS/GCP | 학습 곡선 ↑, 기간 내 부담 |
| Network | nginx + Let's Encrypt + SSH | 인증/포트/방화벽 직접 관리 부담 |
| Network | Cloudflare Tunnel | tailscale 대비 메시 토폴로지 이점 부족 |

## Consequences

### 긍정적
- **비용 통제** — 자체 서버 + flash-lite 조합으로 운영 비용 최저.
- **fallback 친화** — STT 어댑터로 NFR2.3 (LLM 장애 대응) 의 형태소 분석 fallback도 동일 패턴 확장 가능.
- **개발 동질성** — 백엔드와 ML이 같은 Python 런타임 → 직접 임포트 가능.
- **보안** — tailscale 메시로 SSH 키/Public IP 노출 최소.
- **시연 통제** — 자체 서버라 외부 장애에 영향받지 않음.

### 부정적 / 리스크
- 자체 서버 운영 부담 (모니터링·백업·재시작).
- `gemini-3.1-flash-lite-preview` — `preview` 채널의 가용성·계약 변경 리스크. **Mitigation:** ContextAnalyzer 내부에서 모델 ID를 환경변수로 분리.
- tailscale 의존 — tailscale 장애 시 운영자 접근 불가. **Mitigation:** 비상용 SSH 키를 1개 보존.
- Electron + Next.js 셋업 복잡도 — `file://` 프로토콜과 Next.js 라우팅 충돌 가능. **Mitigation:** Hello World 배포(이슈 #5)에서 미리 검증.
- 자체 서버 1대 — 단일 장애점. **Mitigation:** Blue-Green 구성 시 동일 서버 내 컨테이너 이중화 + 향후 2대 분리.

### 후속 조치
- [ ] FastAPI + PostgreSQL 보일러플레이트 (별도 이슈)
- [ ] `STTService` 추상 인터페이스 정의 + 두 어댑터 구현 (Sprint #3 — US-10에 통합)
- [ ] tailscale 서버 셋업 (이슈 #5 Hello World 배포에 포함)
- [ ] Electron + Next.js 보일러플레이트 (이슈 #5)
- [ ] SRS v2 작성 시 §7 도메인 어휘에 `STTService` 가 어댑터임을 명시
- [ ] `gemini-*-preview` GA 전환 시 ADR-0002 후속 ADR로 모델 ID 변경 추적

---

## 참고 자료
- Gemini API: <https://ai.google.dev/>
- Whisper: <https://github.com/openai/whisper>
- wav2vec2 (HuggingFace): <https://huggingface.co/docs/transformers/model_doc/wav2vec2>
- FastAPI: <https://fastapi.tiangolo.com/>
- tailscale: <https://tailscale.com/>
- ADR-0001: [`./0001-electron-as-client-platform.md`](./0001-electron-as-client-platform.md)
