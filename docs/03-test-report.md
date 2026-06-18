# 테스트 보고서 (Test Report)

CWNU 소프트웨어 공학 기말 프로젝트 — **AI 기반 감정 분석 음악 추천 시스템**

| 항목 | 내용 |
|---|---|
| 문서 버전 | v1.0 |
| 제출 마일스톤 | [Phase 2: 테스트 보고서 (W15)](https://github.com/woohyun212/SE-final-project/milestone) |
| 관련 이슈 | [#53](https://github.com/woohyun212/SE-final-project/issues/53) |
| 작성 | 박우현(w00) · 신성민(SmongsDev) · 정원준(Pongchi) |
| 측정 기준일 | 2026-06-18 (`main` 브랜치 기준) |

---

## 1. 개요

본 보고서는 감정 분석 음악 추천 시스템의 **유닛/통합 테스트**, **커버리지 측정 결과**, **발견·수정한 버그 로그**, 그리고 **AI(생성형 LLM)로 작성한 테스트 스크립트 사례**를 정리한다.

시스템은 두 개의 테스트 대상으로 구성된다.

| 대상 | 기술 스택 | 테스트 도구 | 테스트 위치 |
|---|---|---|---|
| **Backend (API/서비스)** | FastAPI · SQLAlchemy · Python 3.12 | `pytest` + `pytest-cov` + `pytest-asyncio` | [`backend/tests/`](../backend/tests/) |
| **Client (UI/로직)** | Electron · Next.js · React · TypeScript | `Jest` + Testing Library | [`client/__tests__/`](../client/__tests__/) |

### 1.1 테스트 전략

- **단위 테스트(Unit)**: 순수 함수·서비스 로직을 외부 의존성(LLM, DB, STT 모델, 네트워크) 없이 검증. 외부 호출은 `monkeypatch`/`jest.mock`으로 대체.
- **통합 테스트(Integration)**: FastAPI `TestClient` + 인메모리 SQLite로 라우터→서비스→DB 전 구간을 검증. 클라이언트는 Testing Library로 컴포넌트+훅+API 어댑터를 함께 렌더링하여 검증.
- **폴백/장애 내성 테스트**: STT·ML·LLM 실패 시 규칙 기반 폴백으로 200 응답을 보장하는지를 별도 스위트(`test_fallback.py`)로 집중 검증.

### 1.2 결과 요약

| 대상 | 통과 | 스킵 | 실패 | 라인 커버리지 | DoD(≥70%) |
|---|---:|---:|---:|---:|:---:|
| Backend (pytest) | **170** | 7 | 0 | **94%** | ✅ |
| Client (Jest) | **244** | 0 | 0 | **95.1%** | ✅ |
| **합계** | **414** | 7 | 0 | — | ✅ |

> 스킵된 7건은 모두 실제 Gemini API 키를 요구하는 라이브 테스트(`@pytest.mark`로 `GEMINI_API_KEY` 미설정 시 자동 skip)로, CI 환경에서는 의도적으로 제외된다.

---

## 2. 테스트 실행 방법 (재현 절차)

### 2.1 Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt          # pytest, pytest-cov, pytest-asyncio 포함
SECRET_KEY=test-secret-key \
  python -m pytest --cov=app --cov-report=term-missing
```

- `conftest.py`가 `SECRET_KEY` 기본값을 주입하므로 환경변수 없이도 수집은 성공하나, 명시 지정 권장(보안 하드닝 PR #66 대응).
- `pyproject.toml`에 `asyncio_mode = "auto"` 설정 — async 테스트는 별도 데코레이터 없이 동작.

### 2.2 Client

```bash
cd client
npm install
npm run test:coverage      # = jest --coverage
```

- `jest.config.js`에 **커버리지 게이트** 설정(NFR4.4): `lib/`·`components/` 전역에서 lines/statements ≥ 85%, branches ≥ 75%, functions ≥ 85% 미만이면 CI 실패.

---

## 3. 단위/통합 테스트 케이스 목록

### 3.1 Backend — 15개 모듈, 177개 케이스 (170 통과 / 7 스킵)

| 테스트 모듈 | 케이스 | 유형 | 검증 영역 |
|---|---:|:---:|---|
| [`test_auth.py`](../backend/tests/test_auth.py) | 21 | 통합 | 회원가입/로그인/토큰 회전/로그아웃, bcrypt 비용, 만료·위조 JWT 거부, 비활성 사용자 차단 |
| [`test_account_deletion.py`](../backend/tests/test_account_deletion.py) | 7 | 통합 | `DELETE /me` 개인정보 전체 파기, 타 사용자 데이터 보존, 삭제 후 토큰 무효화, 이메일 재사용 |
| [`test_context_analyzer.py`](../backend/tests/test_context_analyzer.py) | 23 | 단위 | LLM 컨텍스트 분석 스키마 검증(시간/장소/활동/감정), JSON·마크다운 펜스 파싱, 타임아웃·오류 폴백 |
| [`test_emotion_fusion.py`](../backend/tests/test_emotion_fusion.py) | 21 | 단위 | VAD→오디오 피처 매핑, 경계값 clamp, 감정/컨텍스트 가중 융합 |
| [`test_fallback.py`](../backend/tests/test_fallback.py) | 27 | 단위/통합 | STT·ML·LLM·컨텍스트·이유생성 5개 폴백 경로 및 `fallback_flags` 플래그 |
| [`test_feedback.py`](../backend/tests/test_feedback.py) | 15 | 통합 | 좋아요/싫어요/재생 이벤트 기록, 인증·중복·존재하지 않는 세션/트랙 오류 코드 |
| [`test_feedback_weights.py`](../backend/tests/test_feedback_weights.py) | 8 | 단위 | 피드백 기반 점수 가중치(콜드스타트, 유사 트랙 부스트/페널티, 사용자 격리) |
| [`test_history.py`](../backend/tests/test_history.py) | 7 | 통합 | `GET /history` 정렬·제한·피드백 포함·타 사용자 격리·인증 |
| [`test_recommend.py`](../backend/tests/test_recommend.py) | 12 | 통합 | 추천 10곡 반환, 스키마, 응답 시간, 빈 카탈로그, VAD 영향, DB 저장 |
| [`test_recommendation_results.py`](../backend/tests/test_recommendation_results.py) | 5 | 통합 | 추천 결과 DB 저장·rank/score·세션 격리 |
| [`test_reason_generator.py`](../backend/tests/test_reason_generator.py) | 6 | 단위 | LLM 추천 이유 생성, top-N 제한, 누락·타임아웃·오류 시 규칙 기반 폴백 |
| [`test_stt.py`](../backend/tests/test_stt.py) | 11 | 단위 | Whisper STT 프로토콜, 빈 오디오, 세그먼트 결합, 모델 1회 로드, 싱글톤 |
| [`test_user_preference.py`](../backend/tests/test_user_preference.py) | 7 | 통합 | 선호 프로필 생성·증분 평균·좋아요/싫어요 독립성·점수 상한 |
| [`test_cors.py`](../backend/tests/test_cors.py) | 6 | 통합 | CORS origin 파싱, preflight 허용/차단 헤더 |
| [`test_health.py`](../backend/tests/test_health.py) | 1 | 통합 | 헬스 체크 엔드포인트 |

### 3.2 Client — 21개 스위트, 244개 케이스 (전부 통과)

| 테스트 스위트 | 케이스 | 유형 | 검증 영역 |
|---|---:|:---:|---|
| [`auth.test.ts`](../client/__tests__/auth.test.ts) | 29 | 단위 | 토큰 저장/조회/삭제, JWT exp 파싱, 만료 판정(leeway), refresh 흐름 |
| [`validate.test.ts`](../client/__tests__/validate.test.ts) | 25 | 단위 | 이메일/비밀번호/일치 검증 규칙 |
| [`recommendHandoff.test.ts`](../client/__tests__/recommendHandoff.test.ts) | 18 | 단위 | sessionStorage 핸드오프 저장/로드, 손상 JSON·예외 graceful 처리, NEUTRAL 기본값 |
| [`HistoryList.test.tsx`](../client/__tests__/HistoryList.test.tsx) | 19 | 통합 | 로딩/에러/빈 상태, 접근성(aria), 펼침 토글, rank 정렬, 피드백 배지 |
| [`RecommendationVisualizer.test.tsx`](../client/__tests__/RecommendationVisualizer.test.tsx) | 27 | 통합 | 로딩/에러/빈 상태, 트랙 목록 렌더, 재생시간 포맷, row 액션 렌더 |
| [`EmotionMusicChartRender.test.tsx`](../client/__tests__/EmotionMusicChartRender.test.tsx) | 25 | 통합 | SVG 차트 접근성, 마커/범례/축/사분면, 툴팁 hover·focus·Escape |
| [`RecommendationReasonCard.test.tsx`](../client/__tests__/RecommendationReasonCard.test.tsx) | 19 | 통합 | 트랙 메타 렌더, 재생시간 포맷, 이유 skeleton(로딩) 분기 |
| [`VoiceCapture.test.tsx`](../client/__tests__/VoiceCapture.test.tsx) | 7 | 통합 | 녹음 상태(idle/recording/recorded/too_short/denied), 업로드·재시도, onResult 콜백 |
| [`useVoiceRecorder.test.ts`](../client/__tests__/useVoiceRecorder.test.ts) | 7 | 단위 | 마이크 권한, 녹음 타이머, 자동 종료, 최소 길이 폐기, reset |
| [`usePlaybackLogger.test.tsx`](../client/__tests__/usePlaybackLogger.test.tsx) | 8 | 단위 | 재생 start/end/complete 이벤트, playback_pct, 언마운트 정리, autoplay 차단 롤백 |
| [`useAuthGuard.test.tsx`](../client/__tests__/useAuthGuard.test.tsx) | 10 | 단위 | 인증 가드 리다이렉트, 게스트 가드, 언마운트 후 push 방지 |
| [`useTrackEnrichment.test.tsx`](../client/__tests__/useTrackEnrichment.test.tsx) | 4 | 단위 | preview_url 누락 곡만 보강, track_id 매핑 |
| [`recommendApi.test.ts`](../client/__tests__/recommendApi.test.ts) | 5 | 통합 | `POST /recommend` FormData·Bearer, 401 시 refresh 후 재시도 |
| [`recommendAdapter.test.ts`](../client/__tests__/recommendAdapter.test.ts) | 7 | 단위 | 백엔드 응답 → 클라이언트 모델 매핑, context/fallback_flags |
| [`feedbackApi.test.ts`](../client/__tests__/feedbackApi.test.ts) | 6 | 통합 | 피드백 like/dislike, playback_pct 옵션, history 쿼리 |
| [`FeedbackButtons.test.tsx`](../client/__tests__/FeedbackButtons.test.tsx) | 3 | 통합 | 좋아요 즉시 반영 + API 호출, 세션 없음 disabled, 실패 시 롤백 |
| [`trackEnrichment.test.ts`](../client/__tests__/trackEnrichment.test.ts) | 7 | 단위 | iTunes 보강 응답 매핑, graceful null, 캐시 키 정규화 |
| [`emotionChart.test.ts`](../client/__tests__/emotionChart.test.ts) | 6 | 단위 | valence/energy → SVG 좌표 변환(반전 단조성) |
| [`apiBaseUrl.test.ts`](../client/__tests__/apiBaseUrl.test.ts) | 8 | 단위 | http→https 승격(NFR3.1), localhost 유지, trim |
| [`AudioPlayer.test.tsx`](../client/__tests__/AudioPlayer.test.tsx) | 3 | 통합 | previewUrl 유무 활성화, 재생/일시정지 라벨 |
| [`logoutApi.test.ts`](../client/__tests__/logoutApi.test.ts) | 2 | 통합 | `POST /auth/logout` body·Bearer, 204 void 반환 |

---

## 4. 커버리지 결과

### 4.1 Backend (`pytest --cov=app --cov-report=term-missing`)

```
Name                               Stmts   Miss  Cover   Missing
----------------------------------------------------------------
app/__init__.py                        0      0   100%
app/database.py                       13      4    69%   17-21
app/main.py                           35      3    91%   36-40
app/models/__init__.py                 7      0   100%
app/models/feedback.py                25      0   100%
app/models/music_catalog.py           26      0   100%
app/models/recommendation.py          19      0   100%
app/models/token.py                   11      0   100%
app/models/user.py                    11      0   100%
app/models/user_preference.py         21      0   100%
app/routers/__init__.py                0      0   100%
app/routers/auth.py                  105      4    96%   32, 83-84, 162
app/routers/feedback.py               62      0   100%
app/routers/history.py                25      0   100%
app/routers/recommend.py              74      0   100%
app/schemas/auth.py                   26      0   100%
app/schemas/context.py                46      0   100%
app/schemas/feedback.py                9      0   100%
app/schemas/history.py                20      0   100%
app/schemas/recommend.py              29      0   100%
app/services/context_analyzer.py      65      8    88%   74, 113, 118-123
app/services/emotion_fusion.py        23      0   100%
app/services/ml_client.py             35     11    69%   55, 58-64, 76-79
app/services/reason_generator.py      92     22    76%   29, 33, 37, 39, 53, 95-103, 125, 146, 151-156
app/services/recommendation.py        44      2    95%   15, 17
app/services/stt.py                   39      0   100%
----------------------------------------------------------------
TOTAL                                862     54    94%

================= 170 passed, 7 skipped, 11 warnings in ~28s ==================
```

- **전체 라인 커버리지 94%** — DoD(≥70%) 충족.
- 미커버 구간은 대부분 외부 의존성 경계: `ml_client.py`(원격 ML 서비스 HTTP 예외 경로), `reason_generator.py`/`context_analyzer.py`(실제 LLM 호출 분기 — 라이브 테스트로만 도달).
- `database.py` 17–21행은 운영 PostgreSQL 엔진 초기화 경로로, 테스트는 인메모리 SQLite를 사용하므로 미실행.

### 4.2 Client (`jest --coverage`)

```
-------------------------------|---------|----------|---------|---------|
File                           | % Stmts | % Branch | % Funcs | % Lines |
-------------------------------|---------|----------|---------|---------|
All files                      |   92.72 |    85.38 |   92.59 |    95.1 |
 components                    |   94.44 |    90.22 |   93.67 |   95.72 |
  AudioPlayer.tsx              |     100 |      100 |     100 |     100 |
  EmotionMusicChart.tsx        |   95.94 |    91.11 |   93.33 |   97.05 |
  FeedbackButtons.tsx          |   90.47 |       80 |      75 |      95 |
  HistoryList.tsx              |   93.93 |    93.33 |     100 |   96.55 |
  RecommendationReasonCard.tsx |     100 |      100 |     100 |     100 |
  RecommendationVisualizer.tsx |   93.33 |    85.71 |   91.66 |   93.33 |
  VoiceCapture.tsx             |   93.02 |    89.74 |   88.88 |   93.02 |
 lib                           |   91.99 |    81.71 |   91.56 |   94.82 |
  api.ts                       |    86.3 |    82.85 |      80 |   88.05 |
  auth.ts                      |   92.95 |    78.94 |     100 |   98.36 |
  recommend.ts                 |     100 |    96.55 |     100 |     100 |
  trackEnrichment.ts           |   83.72 |    53.84 |   66.66 |   94.11 |
  useAuthGuard.ts              |     100 |      100 |     100 |     100 |
  usePlaybackLogger.ts         |     100 |      100 |      90 |     100 |
  useTrackEnrichment.ts        |   89.65 |       75 |     100 |     100 |
  useVoiceRecorder.ts          |   89.18 |    65.71 |   93.33 |   90.47 |
  validate.ts                  |     100 |      100 |     100 |     100 |
-------------------------------|---------|----------|---------|---------|
Test Suites: 21 passed, 21 total
Tests:       244 passed, 244 total
```

- **전체 라인 커버리지 95.1% / 구문 92.72% / 브랜치 85.38%** — DoD(≥70%) 및 CI 게이트(NFR4.4) 충족.
- 미커버 브랜치는 주로 브라우저 API 폴백(`useVoiceRecorder.ts`의 미지원 환경 분기, `trackEnrichment.ts`의 네트워크 예외 분기) — jsdom으로 재현 곤란한 일부 경로.

---

## 5. 발견한 버그 로그

테스트 작성·실행 과정에서 발견하여 수정한 주요 결함. 모든 항목은 PR로 추적·머지되었다.

| # | 심각도 | 영역 | 증상 | 원인 | 수정 PR/커밋 |
|---|:---:|---|---|---|---|
| B-01 | High | 추천 점수 | 재방문 사용자의 추천 점수가 비정상적으로 높게 누적 | 선호 프로필 가중치에 점수 상한 미적용 | [#148](https://github.com/woohyun212/SE-final-project/pull/148) `9a25037` |
| B-02 | High | 장애 내성 | STT 실패 시 500 발생 (ML 실패는 폴백되는데 STT는 미흡) | STT 예외가 흡수되지 않아 파이프라인 중단 | `cd8e759` `ab310f5` |
| B-03 | High | CORS | 500 응답에 CORS 헤더가 누락되어 클라이언트가 오류 원인 식별 불가 | 미들웨어 등록 순서 + 예외 처리 누락 | [#141](https://github.com/woohyun212/SE-final-project/pull/141) `972af4c` |
| B-04 | Med | CORS | preflight(OPTIONS) 요청이 거부됨 | `CORSMiddleware` 미등록 | [#70](https://github.com/woohyun212/SE-final-project/issues/70) `edeb4ca` |
| B-05 | Med | 응답 지연 | 추천 응답이 느림(LLM에 전체 트랙 전송) | ReasonGenerator가 모든 트랙에 대해 LLM 호출 | [#177](https://github.com/woohyun212/SE-final-project/issues/177) `c929b1d` |
| B-06 | Med | 클라이언트 | 음성 추천 핸드오프에서 `sessionId` 유실 + transcript 검증 누락 | 어댑터 매핑 시 필드 보존 안 됨 | [#123](https://github.com/woohyun212/SE-final-project/pull/123) `4a0fb4b` |
| B-07 | Med | 클라이언트 | 로그아웃 시 race condition + 감정 라벨 백엔드 불일치 | `EMOTION_KO` 매핑 불일치, logout 비동기 경합 | [#168](https://github.com/woohyun212/SE-final-project/pull/168) `e655027` |
| B-08 | Low | 보안 | `SECRET_KEY` 미설정 시 약한 기본키로 기동 가능 | 환경변수 검증 부재 | [#66](https://github.com/woohyun212/SE-final-project/pull/66) (`conftest.py` 대응) |
| B-09 | Low | 빌드 | Docker 빌드 실패 (`COPY data` 단계) | `dataset.csv`가 Git에 미추가 | [#159](https://github.com/woohyun212/SE-final-project/issues/159) `4c8c212` |
| B-10 | Low | 로깅 | 파이프라인 로그의 `session_id` 포맷 깨짐 | 포맷 지정자 오류 | `16579db` |

> 회귀 방지: B-01은 `test_user_preference.py::test_recommend_warm_user_score_capped`, B-02는 `test_fallback.py::test_stt_failure_returns_200_with_null_transcript`, B-03/B-04는 `test_cors.py`, B-05는 `test_reason_generator.py::test_generate_sends_only_top_n_tracks_to_llm`로 각각 회귀 테스트가 추가되었다.

---

## 6. AI로 생성한 테스트 스크립트 사례

본 프로젝트는 생성형 LLM(Claude / GPT 계열)을 활용해 **테스트 케이스를 초안 생성**하고, 개발자가 도메인 규칙에 맞게 검수·보강하는 워크플로를 사용했다.

### 6.1 워크플로

1. **소스 함수 + 명세를 프롬프트로 제공** — 예: `fuse(valence, arousal, dominance)` 함수 시그니처와 "출력은 0~1로 clamp, 감정/컨텍스트가 가중 융합된다"는 SRS 규칙.
2. **LLM이 경계값·등가분할·반비례 관계 케이스를 제안** — 사람이 놓치기 쉬운 극단값(min/max clamp), 빈 컨텍스트 등가성 등.
3. **개발자 검수** — 마법 상수 대신 `_in_range()`/`_has_all_keys()` 헬퍼로 가독성 보강, 한국어 docstring으로 의도 명시.

### 6.2 생성 사례 — `test_emotion_fusion.py` (감정→오디오 피처 융합)

LLM이 제안한 경계값·반비례 관계 테스트를 검수·정리한 결과:

```python
from app.schemas.context import ContextResult
from app.services.emotion_fusion import fuse

_FEATURES = ("valence", "energy", "danceability", "acousticness", "instrumentalness")

def _in_range(vec: dict[str, float]) -> bool:
    return all(0.0 <= vec[f] <= 1.0 for f in _FEATURES)

def test_vad_neutral_maps_to_midpoint():
    """VAD (0, 0, 0) → valence·energy 모두 0.5"""
    vec = fuse(0.0, 0.0, 0.0)
    assert abs(vec["valence"] - 0.5) < 1e-6
    assert abs(vec["energy"] - 0.5) < 1e-6

def test_acousticness_inverse_of_energy():
    """arousal 상승 → energy 상승, acousticness 하락 (반비례 관계 유지)"""
    low = fuse(0.0, -0.5, 0.0)
    high = fuse(0.0, 0.5, 0.0)
    assert high["energy"] > low["energy"]
    assert high["acousticness"] < low["acousticness"]

def test_output_clamped_extreme_max():
    assert _in_range(fuse(1.0, 1.0, 1.0))   # 극단 입력에서도 0~1 보장
```

> AI는 `test_acousticness_inverse_of_energy`(반비례 불변식)와 극단값 clamp 케이스를 제안했고, 이는 단순 "정상 입력" 테스트만으로는 놓쳤을 회귀 위험을 메웠다.

### 6.3 생성 사례 — `test_fallback.py` (장애 내성)

LLM에 "각 외부 의존성(STT/ML/LLM)이 실패해도 200 응답과 폴백 플래그가 설정되어야 한다"는 NFR을 제공하자, **실패/성공 쌍(pair)** 형태의 테스트를 체계적으로 생성:

```python
def test_stt_fallback_flag_set_when_transcribe_fails(...):
    # STT가 예외를 던지면 fallback_flags.stt == True
    ...

def test_stt_no_fallback_when_transcribe_succeeds(...):
    # 정상 동작 시 플래그가 서지 않는지(거짓 양성 방지)도 함께 검증
    ...
```

이 "성공 경로에서 플래그가 **서지 않음**까지 검증" 패턴은 거짓 양성(false positive)을 막는 핵심으로, AI 제안 후 5개 폴백 경로(STT·ML·컨텍스트·이유생성·VAD) 전체에 일관 적용했다.

### 6.4 효과 및 한계

| 효과 | 한계 / 검수 포인트 |
|---|---|
| 경계값·등가분할·불변식 케이스를 빠르게 망라 (커버리지 단기 확보) | 도메인 임계값(예: `valence > 0.7`)은 사람이 명세와 대조해 조정 필요 |
| 성공/실패 쌍 테스트 패턴 일관 적용 | 모킹 대상(외부 API)을 잘못 짚는 경우가 있어 검수 필수 |
| 한국어 docstring으로 의도 문서화 | 생성된 단언이 "구현을 그대로 베끼는" 토톨로지가 되지 않도록 확인 |

---

## 7. 결론

- 전체 **414개 테스트 전부 통과**(7건은 라이브 API 의존으로 의도적 스킵), 백엔드 라인 커버리지 **94%**, 클라이언트 **95.1%**로 DoD(≥70%) 및 CI 커버리지 게이트(NFR4.4)를 모두 충족한다.
- 테스트 과정에서 발견한 결함(추천 점수 상한·STT 폴백·CORS 등)은 회귀 테스트와 함께 수정·머지되었다.
- AI 생성 테스트는 경계값·불변식·장애 내성 케이스 확보에 기여했으며, 모든 생성물은 도메인 규칙 검수를 거쳐 반영했다.

---

## 부록 A. 측정 환경

| 항목 | 값 |
|---|---|
| OS | Windows 11 + WSL2 (Ubuntu, backend) |
| Python | 3.12.3 |
| pytest / pytest-cov / pytest-asyncio | 8.2.2 / 5.0.0 / 0.23.7 |
| Node.js | nvm4w (Jest 29 계열) |
| Jest 환경 | jsdom + Testing Library (React 18) |
| 브랜치 | `main` |
