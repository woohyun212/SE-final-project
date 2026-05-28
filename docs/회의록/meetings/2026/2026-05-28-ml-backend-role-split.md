# ML · 백엔드 역할 분담 정리

- **일시:** 2026-05-28
- **장소:** 온라인
- **참석자:** @Pongchi, @SmongsDev, @woohyun212
- **불참:** -
- **서기:** @woohyun212
- **회의 종류:** 정기

---

## 1. 안건 (Agenda)
- [x] ML 담당과 백엔드 담당의 작업 범위 구분 명확화
- [x] 추천 파이프라인 각 단계의 책임 주체 확정
- [x] 통합 테스트용 프로토타입 우선순위 결정

## 2. 결정 사항 (Decisions)
> ADR로 남길 가치가 있는 결정은 [`../../decisions/`](../../decisions/) 에 별도 기록.

- **D1.** ML 담당의 작업 범위를 **감정 분석(`EmotionClassifier`)** 으로 한정한다.
- **D2.** STT(`STTService`), LLM 기반 대화/요청 분석(`ContextAnalyzer`), 코사인 유사도 기반 추천(`RecommendationEngine`) 등 추천 파이프라인의 나머지 대부분은 **백엔드**가 담당한다.
- **D3.** 통합 테스트를 위해 **`EmotionClassifier` + LLM API(`ContextAnalyzer`)** 경로의 음악 추천 프로토타입을 최우선으로 개발한다.

## 3. 액션 아이템 (Action Items)

| # | 내용 | 담당 | 마감 | 상태 |
|---|---|---|---|---|
| A1 | 감정 분석 모델(`EmotionClassifier`) 빠르게 학습·준비하여 활용 가능 상태로 | @Pongchi | - | ⏳ |
| A2 | `STTService` / `ContextAnalyzer`(LLM API) / `RecommendationEngine`(코사인 유사도) 백엔드 구현 | @SmongsDev | - | ⏳ |
| A3 | `EmotionClassifier` + LLM API 연동 추천 프로토타입 통합 | @Pongchi, @SmongsDev | - | ⏳ |

## 4. 논의 내용 (Discussion)
- ML 담당과 백엔드 담당의 작업 구분이 그동안 애매하여, 같은 기능을 두고 책임 주체가 불분명한 상황이 있었음.
- 추천 파이프라인을 단계별로 나눠 책임을 명확히 하기로 함:
  - **감정 분석(`EmotionClassifier`)** → ML 담당
  - **STT(`STTService`) · LLM 대화/요청 분석(`ContextAnalyzer`) · 코사인 유사도 추천(`RecommendationEngine`)** → 백엔드 담당
- 즉, ML은 감정 분석에 집중하고, 추천 파이프라인의 데이터 처리·외부 API 연동·유사도 계산은 백엔드가 가져가는 구조.
- 전체 흐름을 빠르게 검증하기 위해, 완성형 모델을 기다리기보다 **ML(감정 분석) + LLM API** 를 엮은 음악 추천 프로토타입을 먼저 만들어 end-to-end 테스트를 진행하기로 함.
- ML 담당은 이에 맞춰 모델 학습을 빠르게 진행해 활용 가능한 상태로 준비.

## 5. 보류/다음 회의 안건 (Parking Lot)
- 프로토타입에서 감정 분석 결과와 LLM 컨텍스트를 결합하는 방식(`EmotionFusion`)의 구체 설계.
- 역할 경계(ML ↔ 백엔드)가 더 굳어지면 ADR로 승격할지 검토.

---

## 참고 링크
- 관련 SRS: [`../../design/srs-v1.md`](../../design/srs-v1.md)
- 관련 ADR: (없음)
