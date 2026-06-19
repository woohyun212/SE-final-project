"""NFR4.1 추천 좋아요율(like rate) 평가 스크립트.

추천 결과에 대한 사용자 피드백 중 좋아요 비율을 산출한다 (FR6.1 like/dislike).
최종 보고서(#55)의 NFR4.1(좋아요율 >= 50%) 근거 자료 생성용.

  like_rate = like_count / (like_count + dislike_count)

## 운영 기간 제약 (중요)
이 지표는 **실사용 피드백 데이터**가 있어야 의미를 갖는다. 프로젝트 운영 기간이
짧아 충분한 표본을 확보하지 못하면 "표본 없음 → 미측정"으로 보고하되, 본 스크립트로
**측정 방법론·자동화는 완비**해 둔다. 운영 데이터가 쌓이면 #200 과 동일한 docker
핸드오프로 즉시 산출할 수 있다.

## 실행 (운영 데이터가 쌓인 뒤)
  python -m scripts.eval_like_rate                       # DATABASE_URL 사용
  python -m scripts.eval_like_rate --threshold 0.5 --out report.md --json

종료 코드: 표본이 있고 like_rate >= threshold 면 0, 그 외(미달/표본없음) 1.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback, FeedbackType

DEFAULT_THRESHOLD = 0.5


@dataclass
class LikeRateResult:
    like_count: int
    dislike_count: int
    threshold: float

    @property
    def total(self) -> int:
        return self.like_count + self.dislike_count

    @property
    def has_data(self) -> bool:
        return self.total > 0

    @property
    def like_rate(self) -> float:
        return self.like_count / self.total if self.total else 0.0

    @property
    def passed(self) -> bool:
        # 표본이 없으면 충족 판정 불가(미측정) → False.
        return self.has_data and self.like_rate >= self.threshold


def evaluate_like_rate(db: Session, threshold: float = DEFAULT_THRESHOLD) -> LikeRateResult:
    """feedbacks 테이블의 like/dislike 수를 집계해 좋아요율 계산."""

    def _count(ftype: FeedbackType) -> int:
        stmt = select(func.count()).select_from(Feedback).where(Feedback.feedback_type == ftype)
        return int(db.scalar(stmt) or 0)

    return LikeRateResult(
        like_count=_count(FeedbackType.like),
        dislike_count=_count(FeedbackType.dislike),
        threshold=threshold,
    )


def render_markdown(result: LikeRateResult) -> str:
    """최종 보고서에 붙일 수 있는 마크다운."""
    lines = [
        "# NFR4.1 — 추천 좋아요율 평가 결과",
        "",
        "**정의**: like_rate = 좋아요 / (좋아요 + 싫어요)  ·  목표 >= "
        f"{result.threshold:.0%}",
        "",
        "| 좋아요 | 싫어요 | 합계 | 좋아요율 |",
        "|---|---|---|---|",
        f"| {result.like_count} | {result.dislike_count} | {result.total} | "
        + (f"{result.like_rate:.1%}" if result.has_data else "—")
        + " |",
        "",
    ]
    if not result.has_data:
        lines.append(
            "**판정**: 표본 없음 — 운영 기간 제약으로 실사용 피드백 미확보. "
            "측정 도구·방법론은 완비(본 스크립트), 운영 데이터 확보 시 즉시 산출 가능. (미측정)"
        )
    else:
        verdict = "충족" if result.passed else "미충족"
        lines.append(
            f"**판정**: 좋아요율 {result.like_rate:.1%} "
            f"(목표 >= {result.threshold:.0%}, 표본 {result.total}건) -> {verdict}"
        )
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
    parser = argparse.ArgumentParser(description="NFR4.1 좋아요율 평가")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--out", help="마크다운 리포트 저장 경로 (생략 시 stdout)")
    parser.add_argument("--json", action="store_true", help="JSON 으로도 출력")
    args = parser.parse_args(argv)

    db = _open_session(args.db_url)
    try:
        result = evaluate_like_rate(db, threshold=args.threshold)
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
                    "like_count": result.like_count,
                    "dislike_count": result.dislike_count,
                    "total": result.total,
                    "like_rate": result.like_rate,
                    "threshold": result.threshold,
                    "has_data": result.has_data,
                    "passed": result.passed,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
