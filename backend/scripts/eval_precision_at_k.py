"""NFR4.2 Precision@10 오프라인 평가 스크립트.

추천 엔진(`recommend_by_emotion`)이 감정 질의에 대해 **감정적으로 적절한** 곡을
상위 K개에 얼마나 담는지를 정량화한다. 최종 보고서(#55)의 NFR4.2(Precision@10 ≥ 0.4)
근거 자료로 사용한다.

## Relevance 정의 (라벨 없는 오프라인 평가)
사람 관련성 라벨이 없으므로, **valence×energy 2D 감정 평면의 사분면 일치**를
relevance 기준으로 삼는다. 질의 감정점이 속한 사분면(예: 긍정·활기)과 같은
사분면에 있는 추천 곡을 "관련 있음"으로 본다. 0.5 를 각 축의 분기점으로 사용한다.

  relevant(track | query) :=
      (track.valence >= 0.5) == (query.valence >= 0.5)
      AND (track.energy  >= 0.5) == (query.energy  >= 0.5)

Precision@K = (top-K 중 관련 곡 수) / K,  질의 집합 평균이 최종 지표.

근거: 이 시스템의 추천 가치는 "입력 감정과 어울리는 곡"을 주는 것이므로(SRS FR4.1),
감정 사분면 적합도가 관련성의 1차 프록시로 타당하다. 한계는 보고서에 함께 기술한다.

## 실행
  # 운영 DB(시드된 music_catalog) 대상
  python -m scripts.eval_precision_at_k                     # DATABASE_URL 사용
  python -m scripts.eval_precision_at_k --db-url postgresql+psycopg://... --out report.md

종료 코드: 평균 Precision@K >= threshold 면 0, 미만이면 1 (CI 게이트로도 사용 가능).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.music_catalog import MusicCatalog
from app.services.recommendation import recommend_by_emotion

# 중립값 — 질의 벡터에서 valence/energy 외 feature 는 중립으로 둬 두 감정축이 지배하게 한다.
_NEUTRAL = 0.5
_SPLIT = 0.5
DEFAULT_K = 10
DEFAULT_THRESHOLD = 0.4


@dataclass(frozen=True)
class EmotionQuery:
    """평가 질의 — 이름 + valence/energy 목표점. 사분면은 0.5 분기로 파생."""

    name: str
    valence: float
    energy: float

    def to_emotion_vector(self) -> dict[str, float]:
        """recommend_by_emotion 이 받는 feature dict (나머지는 중립)."""
        return {
            "danceability": _NEUTRAL,
            "energy": self.energy,
            "valence": self.valence,
            "acousticness": _NEUTRAL,
            "instrumentalness": _NEUTRAL,
        }


# valence×energy 4사분면 + 축 경계를 고르게 덮는 기본 질의 집합.
DEFAULT_QUERIES: tuple[EmotionQuery, ...] = (
    EmotionQuery("기쁨·활기 (긍정·고에너지)", valence=0.85, energy=0.85),
    EmotionQuery("평온 (긍정·저에너지)", valence=0.80, energy=0.20),
    EmotionQuery("긴장·분노 (부정·고에너지)", valence=0.20, energy=0.85),
    EmotionQuery("우울 (부정·저에너지)", valence=0.15, energy=0.15),
    EmotionQuery("설렘 (긍정·중상 에너지)", valence=0.75, energy=0.65),
    EmotionQuery("침잠 (부정·중하 에너지)", valence=0.25, energy=0.35),
)


def is_relevant(track: MusicCatalog, query: EmotionQuery) -> bool:
    """track 이 query 와 같은 valence×energy 사분면에 있으면 관련 있음."""
    return (track.valence >= _SPLIT) == (query.valence >= _SPLIT) and (
        track.energy >= _SPLIT
    ) == (query.energy >= _SPLIT)


@dataclass
class QueryResult:
    name: str
    relevant: int
    k: int

    @property
    def precision(self) -> float:
        return self.relevant / self.k if self.k else 0.0


@dataclass
class EvalResult:
    per_query: list[QueryResult]
    k: int
    threshold: float

    @property
    def mean_precision(self) -> float:
        if not self.per_query:
            return 0.0
        return sum(q.precision for q in self.per_query) / len(self.per_query)

    @property
    def passed(self) -> bool:
        return self.mean_precision >= self.threshold


def evaluate_precision_at_k(
    db: Session,
    queries: tuple[EmotionQuery, ...] = DEFAULT_QUERIES,
    k: int = DEFAULT_K,
    threshold: float = DEFAULT_THRESHOLD,
) -> EvalResult:
    """각 질의에 대해 top-K 추천을 받아 사분면 관련도로 Precision@K 계산.

    user_id=None 으로 호출해 피드백 가중치 없는 **순수 콘텐츠 기반** 추천을 평가한다
    (지표 재현성 확보 — 개인화는 별도 지표 영역).
    """
    per_query: list[QueryResult] = []
    for q in queries:
        recs = recommend_by_emotion(db, q.to_emotion_vector(), user_id=None, top_k=k)
        relevant = sum(1 for track, _score in recs if is_relevant(track, q))
        per_query.append(QueryResult(name=q.name, relevant=relevant, k=len(recs)))
    return EvalResult(per_query=per_query, k=k, threshold=threshold)


def render_markdown(result: EvalResult) -> str:
    """최종 보고서에 붙일 수 있는 마크다운 표."""
    lines = [
        f"# NFR4.2 — Precision@{result.k} 평가 결과",
        "",
        "**Relevance 기준**: valence×energy 사분면 일치 (0.5 분기).",
        "**개인화 제외**: user_id=None (순수 콘텐츠 기반).",
        "",
        "| 감정 질의 | 관련/반환 | Precision |",
        "|---|---|---|",
    ]
    for q in result.per_query:
        lines.append(f"| {q.name} | {q.relevant}/{q.k} | {q.precision:.3f} |")
    verdict = "충족" if result.passed else "미충족"
    lines += [
        f"| **평균** |  | **{result.mean_precision:.3f}** |",
        "",
        f"**판정**: 평균 Precision@{result.k} = {result.mean_precision:.3f} "
        f"(목표 >= {result.threshold}) -> {verdict}",
    ]
    return "\n".join(lines)


def _open_session(db_url: str | None) -> Session:
    """--db-url 또는 DATABASE_URL 로 세션 생성. 미지정 시 app.database 기본 사용."""
    if db_url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(db_url)
        return sessionmaker(bind=engine)()
    from app.database import SessionLocal  # 지연 import — 환경변수 의존

    return SessionLocal()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NFR4.2 Precision@K 평가")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--out", help="마크다운 리포트 저장 경로 (생략 시 stdout)")
    parser.add_argument("--json", action="store_true", help="JSON 으로도 출력")
    args = parser.parse_args(argv)

    db = _open_session(args.db_url)
    try:
        result = evaluate_precision_at_k(db, k=args.k, threshold=args.threshold)
    finally:
        db.close()

    md = render_markdown(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        print(f"리포트 저장: {args.out}")
    else:
        print(md)

    if args.json:
        print(
            json.dumps(
                {
                    "k": result.k,
                    "threshold": result.threshold,
                    "mean_precision": result.mean_precision,
                    "passed": result.passed,
                    "per_query": [
                        {
                            "name": q.name,
                            "relevant": q.relevant,
                            "k": q.k,
                            "precision": q.precision,
                        }
                        for q in result.per_query
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
