"""NFR4.2 Precision@K 평가 스크립트 테스트.

사분면을 통제한 인메모리 catalog 로 결정적 검증:
- is_relevant 사분면 판정 로직
- evaluate_precision_at_k end-to-end (관련 곡이 top-K 를 지배 → precision 1.0)
- 빈 catalog / threshold 판정 / 마크다운 렌더
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.music_catalog import MusicCatalog
from scripts.eval_precision_at_k import (
    DEFAULT_QUERIES,
    EmotionQuery,
    EvalResult,
    QueryResult,
    evaluate_precision_at_k,
    is_relevant,
    render_markdown,
)

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _row(i: int, *, valence: float, energy: float) -> MusicCatalog:
    """다른 feature 는 중립(0.5) 고정 — valence/energy 사분면만 통제."""
    return MusicCatalog(
        track_id=f"trk_{i:03d}",
        id=i + 1,
        track_name=f"Track {i}",
        artists=f"Artist {i}",
        album_name=f"Album {i}",
        track_genre="pop",
        popularity=50,
        duration_ms=200_000,
        preview_url=None,
        danceability=0.5,
        energy=energy,
        valence=valence,
        acousticness=0.5,
        instrumentalness=0.5,
        speechiness=0.05,
        liveness=0.1,
        tempo=120.0,
        loudness=-8.0,
        key=0,
        mode=1,
        time_signature=4,
    )


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _seed(rows: list[MusicCatalog]) -> None:
    db = TestingSessionLocal()
    db.add_all(rows)
    db.commit()
    db.close()


def _seed_four_quadrants(per_quadrant: int = 10) -> None:
    """4사분면 각 per_quadrant 곡 — 극단값으로 사분면을 또렷이 분리."""
    rows = []
    i = 0
    for v, e in ((0.9, 0.9), (0.9, 0.1), (0.1, 0.9), (0.1, 0.1)):
        for _ in range(per_quadrant):
            rows.append(_row(i, valence=v, energy=e))
            i += 1
    _seed(rows)


# ── is_relevant ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "tv,te,qv,qe,expected",
    [
        (0.9, 0.9, 0.8, 0.8, True),   # 같은 사분면(긍정·고)
        (0.1, 0.1, 0.8, 0.8, False),  # 반대 사분면
        (0.9, 0.1, 0.8, 0.2, True),   # 긍정·저 일치
        (0.1, 0.9, 0.2, 0.8, True),   # 부정·고 일치
        (0.9, 0.9, 0.8, 0.2, False),  # energy 사분면 불일치
        (0.5, 0.5, 0.8, 0.8, True),   # 경계값 0.5 는 high 로 취급
    ],
)
def test_is_relevant_quadrant(tv, te, qv, qe, expected):
    track = _row(0, valence=tv, energy=te)
    query = EmotionQuery("q", valence=qv, energy=qe)
    assert is_relevant(track, query) is expected


# ── evaluate_precision_at_k ──────────────────────────────────────────────────


def test_matching_quadrant_dominates_topk():
    """관련 사분면 곡이 top-K 를 채우면 precision 1.0."""
    _seed_four_quadrants(per_quadrant=10)
    db = TestingSessionLocal()
    try:
        res = evaluate_precision_at_k(
            db, queries=(EmotionQuery("긍정·고", valence=0.85, energy=0.85),), k=10
        )
    finally:
        db.close()
    assert res.per_query[0].k == 10
    assert res.per_query[0].precision == 1.0
    assert res.passed is True


def test_full_default_query_set_passes():
    """4사분면 균등 catalog 에서 기본 질의셋 평균이 임계값을 넘는다."""
    _seed_four_quadrants(per_quadrant=10)
    db = TestingSessionLocal()
    try:
        res = evaluate_precision_at_k(db, queries=DEFAULT_QUERIES, k=10, threshold=0.4)
    finally:
        db.close()
    assert len(res.per_query) == len(DEFAULT_QUERIES)
    assert res.mean_precision >= 0.4
    assert res.passed is True


def test_opposite_quadrant_yields_zero_precision():
    """catalog 가 전부 긍정·고 사분면이면 부정·저 질의의 precision 은 0."""
    _seed([_row(i, valence=0.9, energy=0.9) for i in range(15)])
    db = TestingSessionLocal()
    try:
        res = evaluate_precision_at_k(
            db, queries=(EmotionQuery("부정·저", valence=0.1, energy=0.1),), k=10
        )
    finally:
        db.close()
    assert res.per_query[0].precision == 0.0
    assert res.passed is False


def test_empty_catalog():
    """빈 catalog → 반환 0, precision 0, 미충족."""
    db = TestingSessionLocal()
    try:
        res = evaluate_precision_at_k(
            db, queries=(EmotionQuery("q", valence=0.8, energy=0.8),), k=10
        )
    finally:
        db.close()
    assert res.per_query[0].k == 0
    assert res.per_query[0].precision == 0.0
    assert res.passed is False


def test_k_caps_to_catalog_size():
    """catalog 가 K 보다 작으면 k 는 catalog 크기로 제한."""
    _seed([_row(i, valence=0.9, energy=0.9) for i in range(4)])
    db = TestingSessionLocal()
    try:
        res = evaluate_precision_at_k(
            db, queries=(EmotionQuery("긍정·고", valence=0.85, energy=0.85),), k=10
        )
    finally:
        db.close()
    assert res.per_query[0].k == 4
    assert res.per_query[0].precision == 1.0


# ── EvalResult / render ──────────────────────────────────────────────────────


def test_eval_result_threshold_logic():
    below = EvalResult([QueryResult("a", 3, 10), QueryResult("b", 4, 10)], k=10, threshold=0.4)
    assert below.mean_precision == pytest.approx(0.35)
    assert below.passed is False

    at = EvalResult([QueryResult("a", 4, 10)], k=10, threshold=0.4)
    assert at.mean_precision == pytest.approx(0.4)
    assert at.passed is True


def test_render_markdown_contains_summary():
    res = EvalResult([QueryResult("기쁨", 8, 10)], k=10, threshold=0.4)
    md = render_markdown(res)
    assert "Precision@10" in md
    assert "기쁨" in md
    assert "0.800" in md
    assert "충족" in md
