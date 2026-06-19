"""NFR4.1 좋아요율 평가 스크립트 테스트.

인메모리 sqlite 에 Feedback 을 시드해 결정적 검증:
- 좋아요율 계산·임계값 판정
- 표본 없음(운영기간 제약) → 미측정(passed False)
- 마크다운 렌더
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (모든 모델 등록 — FK 대상 테이블 생성)
from app.database import Base
from app.models.feedback import Feedback, FeedbackType
from scripts.eval_like_rate import (
    LikeRateResult,
    evaluate_like_rate,
    render_markdown,
)

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _seed_feedback(likes: int, dislikes: int) -> None:
    """sqlite 는 기본적으로 FK 미강제 → 부모 행 없이 Feedback 직접 삽입."""
    db = TestingSessionLocal()
    i = 0
    for _ in range(likes):
        db.add(Feedback(user_id=1, track_id=f"t{i}", recommendation_id="s1", feedback_type=FeedbackType.like))
        i += 1
    for _ in range(dislikes):
        db.add(Feedback(user_id=1, track_id=f"t{i}", recommendation_id="s1", feedback_type=FeedbackType.dislike))
        i += 1
    db.commit()
    db.close()


# ── evaluate_like_rate ───────────────────────────────────────────────────────


def test_like_rate_above_threshold_passes():
    _seed_feedback(likes=7, dislikes=3)
    db = TestingSessionLocal()
    try:
        res = evaluate_like_rate(db, threshold=0.5)
    finally:
        db.close()
    assert res.like_count == 7
    assert res.dislike_count == 3
    assert res.total == 10
    assert res.like_rate == pytest.approx(0.7)
    assert res.passed is True


def test_like_rate_below_threshold_fails():
    _seed_feedback(likes=3, dislikes=7)
    db = TestingSessionLocal()
    try:
        res = evaluate_like_rate(db, threshold=0.5)
    finally:
        db.close()
    assert res.like_rate == pytest.approx(0.3)
    assert res.passed is False


def test_like_rate_exactly_at_threshold_passes():
    _seed_feedback(likes=5, dislikes=5)
    db = TestingSessionLocal()
    try:
        res = evaluate_like_rate(db, threshold=0.5)
    finally:
        db.close()
    assert res.like_rate == pytest.approx(0.5)
    assert res.passed is True


def test_no_feedback_is_unmeasured():
    """표본 없음 → 운영기간 제약, 미측정(passed False, has_data False)."""
    db = TestingSessionLocal()
    try:
        res = evaluate_like_rate(db, threshold=0.5)
    finally:
        db.close()
    assert res.total == 0
    assert res.has_data is False
    assert res.like_rate == 0.0
    assert res.passed is False


# ── LikeRateResult / render ──────────────────────────────────────────────────


def test_render_with_data():
    md = render_markdown(LikeRateResult(like_count=8, dislike_count=2, threshold=0.5))
    assert "NFR4.1" in md
    assert "80.0%" in md
    assert "충족" in md


def test_render_no_data_states_unmeasured():
    md = render_markdown(LikeRateResult(like_count=0, dislike_count=0, threshold=0.5))
    assert "표본 없음" in md
    assert "미측정" in md
