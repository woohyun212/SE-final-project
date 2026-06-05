"""누적 피드백 가중치 반영 테스트 (#49)

recommend_by_emotion()에 user_id를 전달할 때:
- cold start: 피드백 없으면 순수 감정 벡터 기반 순위
- 좋아요 boost: 좋아요 곡과 유사한 트랙이 상위로 올라옴
- 싫어요 penalty: 싫어요 곡과 유사한 트랙이 하위로 내려옴
- 점수 clip: 최종 점수 ≥ 0
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base
from app.models.feedback import Feedback, FeedbackType
from app.models.music_catalog import MusicCatalog
from app.models.recommendation import RecommendationSession
from app.models.user_preference import UserPreference, _FEATURE_COLS as PREF_COLS
from app.services.recommendation import recommend_by_emotion

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Session = sessionmaker(bind=engine)


def _catalog_row(track_id: str, **features) -> MusicCatalog:
    defaults = dict(
        id=None,
        track_name=track_id,
        artists="Artist",
        album_name="Album",
        track_genre="pop",
        popularity=50,
        duration_ms=200_000,
        danceability=0.5,
        energy=0.5,
        valence=0.5,
        acousticness=0.1,
        instrumentalness=0.0,
        speechiness=0.05,
        liveness=0.1,
        tempo=120.0,
        loudness=-8.0,
        key=0,
        mode=1,
        time_signature=4,
    )
    defaults.update(features)
    return MusicCatalog(track_id=track_id, **defaults)


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def session():
    s = Session()
    yield s
    s.close()


def _add_feedback(session, user_id: int, track_id: str, feedback_type: FeedbackType) -> None:
    rec = RecommendationSession(user_id=user_id, user_valence=0.5, user_energy=0.5)
    session.add(rec)
    session.flush()
    session.add(Feedback(
        user_id=user_id,
        track_id=track_id,
        recommendation_id=rec.id,
        feedback_type=feedback_type,
    ))

    # UserPreference 갱신 — feedback 라우터의 _upsert_preference 동작 모사
    track = session.get(MusicCatalog, track_id)
    pref = session.get(UserPreference, user_id)
    if pref is None:
        pref = UserPreference(
            user_id=user_id,
            like_danceability=0.0, like_energy=0.0, like_valence=0.0,
            like_acousticness=0.0, like_instrumentalness=0.0, like_count=0,
            dislike_danceability=0.0, dislike_energy=0.0, dislike_valence=0.0,
            dislike_acousticness=0.0, dislike_instrumentalness=0.0, dislike_count=0,
            updated_at=datetime.now(UTC),
        )
        session.add(pref)
        session.flush()
    track_vec = [getattr(track, f) for f in PREF_COLS]
    if feedback_type == FeedbackType.like:
        new_count = pref.like_count + 1
        for f, v in zip(PREF_COLS, track_vec):
            old = getattr(pref, f"like_{f}")
            setattr(pref, f"like_{f}", old + (v - old) / new_count)
        pref.like_count = new_count
    else:
        new_count = pref.dislike_count + 1
        for f, v in zip(PREF_COLS, track_vec):
            old = getattr(pref, f"dislike_{f}")
            setattr(pref, f"dislike_{f}", old + (v - old) / new_count)
        pref.dislike_count = new_count
    session.commit()


# ── cold start ─────────────────────────────────────────────────────────────────

def test_cold_start_no_error(session) -> None:
    """피드백 없는 신규 사용자도 정상 추천 반환 (에러 없이 전체 트랙 반환)"""
    session.add(_catalog_row("t1", danceability=0.8, energy=0.8, valence=0.8))
    session.add(_catalog_row("t2", danceability=0.2, energy=0.2, valence=0.2))
    session.commit()

    results = recommend_by_emotion(session, {"valence": 0.8, "energy": 0.8}, user_id=1)
    assert len(results) == 2
    assert {t.track_id for t, _ in results} == {"t1", "t2"}


def test_cold_start_same_as_no_user_id(session) -> None:
    """피드백 없을 때 user_id 전달 결과 == user_id=None 결과"""
    for i in range(5):
        session.add(_catalog_row(f"t{i}", danceability=round(0.2 * i, 1)))
    session.commit()

    ev = {"valence": 0.5, "energy": 0.5}
    with_user = [t.track_id for t, _ in recommend_by_emotion(session, ev, user_id=99)]
    without_user = [t.track_id for t, _ in recommend_by_emotion(session, ev, user_id=None)]
    assert with_user == without_user


# ── 좋아요 boost ──────────────────────────────────────────────────────────────

def test_like_boosts_similar_tracks(session) -> None:
    """좋아요한 곡과 feature가 비슷한 곡이 그렇지 않은 곡보다 상위에 랭크됨"""
    # liked_track: high danceability/energy/valence
    session.add(_catalog_row("liked", danceability=0.9, energy=0.9, valence=0.9, acousticness=0.0, instrumentalness=0.0))
    # similar to liked
    session.add(_catalog_row("similar", danceability=0.85, energy=0.85, valence=0.85, acousticness=0.05, instrumentalness=0.0))
    # dissimilar
    session.add(_catalog_row("dissimilar", danceability=0.1, energy=0.1, valence=0.1, acousticness=0.9, instrumentalness=0.9))
    session.commit()

    _add_feedback(session, user_id=1, track_id="liked", feedback_type=FeedbackType.like)

    ev = {"valence": 0.5, "energy": 0.5, "danceability": 0.5}
    results = recommend_by_emotion(session, ev, user_id=1)
    track_ids = [t.track_id for t, _ in results]

    # liked 자체는 포함되고, similar가 dissimilar보다 위에 있어야 함
    assert "liked" in track_ids
    assert track_ids.index("similar") < track_ids.index("dissimilar")


def test_like_increases_score_vs_cold_start(session) -> None:
    """좋아요 이후 유사 곡의 점수가 cold start보다 높아야 함"""
    session.add(_catalog_row("liked", danceability=0.9, energy=0.9, valence=0.9))
    session.add(_catalog_row("similar", danceability=0.85, energy=0.85, valence=0.85))
    session.commit()

    ev = {"valence": 0.5, "energy": 0.5}
    cold_scores = {t.track_id: s for t, s in recommend_by_emotion(session, ev, user_id=None)}

    _add_feedback(session, user_id=1, track_id="liked", feedback_type=FeedbackType.like)
    warm_scores = {t.track_id: s for t, s in recommend_by_emotion(session, ev, user_id=1)}

    assert warm_scores["similar"] > cold_scores["similar"]


# ── 싫어요 penalty ─────────────────────────────────────────────────────────────

def test_dislike_penalizes_similar_tracks(session) -> None:
    """싫어요한 곡과 feature가 비슷한 곡이 dissimilar보다 하위에 랭크됨"""
    session.add(_catalog_row("disliked", danceability=0.9, energy=0.9, valence=0.9, acousticness=0.0, instrumentalness=0.0))
    session.add(_catalog_row("similar", danceability=0.85, energy=0.85, valence=0.85, acousticness=0.05, instrumentalness=0.0))
    session.add(_catalog_row("dissimilar", danceability=0.1, energy=0.1, valence=0.1, acousticness=0.9, instrumentalness=0.9))
    session.commit()

    _add_feedback(session, user_id=1, track_id="disliked", feedback_type=FeedbackType.dislike)

    ev = {"valence": 0.5, "energy": 0.5}
    results = recommend_by_emotion(session, ev, user_id=1)
    track_ids = [t.track_id for t, _ in results]

    # dissimilar이 similar보다 위에 있어야 함 (싫어요 페널티)
    assert track_ids.index("dissimilar") < track_ids.index("similar")


def test_dislike_decreases_score_vs_cold_start(session) -> None:
    """싫어요 이후 유사 곡의 점수가 cold start보다 낮아야 함"""
    session.add(_catalog_row("disliked", danceability=0.9, energy=0.9, valence=0.9))
    session.add(_catalog_row("similar", danceability=0.85, energy=0.85, valence=0.85))
    session.commit()

    ev = {"valence": 0.5, "energy": 0.5}
    cold_scores = {t.track_id: s for t, s in recommend_by_emotion(session, ev, user_id=None)}

    _add_feedback(session, user_id=1, track_id="disliked", feedback_type=FeedbackType.dislike)
    warm_scores = {t.track_id: s for t, s in recommend_by_emotion(session, ev, user_id=1)}

    assert warm_scores["similar"] < cold_scores["similar"]


# ── 점수 clip ──────────────────────────────────────────────────────────────────

def test_scores_are_non_negative(session) -> None:
    """싫어요 페널티가 강해도 최종 점수 ≥ 0"""
    for i in range(5):
        session.add(_catalog_row(f"t{i}", danceability=round(0.1 + 0.2 * i, 1)))
    session.commit()

    # 여러 개 싫어요
    for i in range(3):
        _add_feedback(session, user_id=1, track_id=f"t{i}", feedback_type=FeedbackType.dislike)

    results = recommend_by_emotion(session, {"valence": 0.5}, user_id=1)
    assert all(score >= 0.0 for _, score in results)


# ── 다른 사용자 피드백 격리 ────────────────────────────────────────────────────

def test_other_user_feedback_not_applied(session) -> None:
    """user_id=2 피드백이 user_id=1 추천에 영향을 주지 않아야 함"""
    session.add(_catalog_row("t1", danceability=0.9, energy=0.9, valence=0.9))
    session.add(_catalog_row("t2", danceability=0.1, energy=0.1, valence=0.1))
    session.commit()

    # user 2가 t1을 좋아요
    _add_feedback(session, user_id=2, track_id="t1", feedback_type=FeedbackType.like)

    ev = {"valence": 0.5, "energy": 0.5}
    user1_results = recommend_by_emotion(session, ev, user_id=1)
    cold_results = recommend_by_emotion(session, ev, user_id=None)

    # user 1은 피드백 없으므로 cold start와 동일 순서
    assert [t.track_id for t, _ in user1_results] == [t.track_id for t, _ in cold_results]
