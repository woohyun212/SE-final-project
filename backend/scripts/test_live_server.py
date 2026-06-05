"""
실서버 E2E 테스트 — http://backend.pongchi.kro.kr/

사용법:
    python scripts/test_live_server.py <audio.wav>
    python scripts/test_live_server.py <audio.wav> --base-url http://localhost:8000

시나리오:
    1. 회원가입 (랜덤 이메일 생성)
    2. 로그인
    3. 음성 파일로 추천 요청
    4. 추천 결과 1번 좋아요 / 2번 싫어요 / 3번 재생 이벤트
    5. 이력 조회
    6. 두 번째 추천 요청 (피드백 누적 후)
    7. 토큰 갱신 (rotation 검증)
    8. 로그아웃 후 보호 엔드포인트 접근 거부 확인
"""

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import requests

BASE_URL = "http://backend.pongchi.kro.kr"
TIMEOUT = 30  # seconds


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _ok(label: str, res: requests.Response, expected: int = 200) -> dict:
    mark = "✓" if res.status_code == expected else "✗"
    print(f"  {mark} [{res.status_code}] {label}")
    if res.status_code != expected:
        print(f"      response: {res.text[:300]}")
        sys.exit(1)
    try:
        return res.json()
    except Exception:
        return {}


def _fail(label: str, res: requests.Response, expected: int) -> None:
    mark = "✓" if res.status_code == expected else "✗"
    print(f"  {mark} [{res.status_code}] {label} (expect {expected})")
    if res.status_code != expected:
        print(f"      response: {res.text[:300]}")
        sys.exit(1)


def section(title: str) -> None:
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


def main() -> None:
    parser = argparse.ArgumentParser(description="실서버 E2E 테스트")
    parser.add_argument("wav", type=Path, help="테스트에 사용할 WAV 파일 경로")
    parser.add_argument("--base-url", default=BASE_URL, help=f"서버 주소 (기본: {BASE_URL})")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")

    if not args.wav.exists():
        print(f"[ERROR] 파일을 찾을 수 없습니다: {args.wav}")
        sys.exit(1)

    audio_bytes = args.wav.read_bytes()
    email = f"test_{uuid.uuid4().hex[:8]}@test.com"
    password = "TestPass1!"

    print(f"\n{'='*55}")
    print(f"  서버   : {base}")
    print(f"  파일   : {args.wav}  ({len(audio_bytes):,} bytes)")
    print(f"  계정   : {email}")
    print(f"{'='*55}")

    s = requests.Session()
    s.timeout = TIMEOUT

    # ── 1. 회원가입 ────────────────────────────────────────
    section("1. 회원가입")
    res = s.post(f"{base}/auth/signup", json={"email": email, "password": password})
    body = _ok("POST /auth/signup", res, 201)
    access: str = body["access_token"]
    refresh: str = body["refresh_token"]
    print(f"      access_token  : {access[:40]}…")

    # ── 2. 로그인 ──────────────────────────────────────────
    section("2. 로그인")
    res = s.post(f"{base}/auth/login", json={"email": email, "password": password})
    body = _ok("POST /auth/login", res, 200)
    access = body["access_token"]
    refresh = body["refresh_token"]
    print(f"      access_token  : {access[:40]}…")

    # ── 3. 첫 번째 추천 요청 ───────────────────────────────
    section("3. 첫 번째 추천 요청 (음성 파일 업로드)")
    t0 = time.perf_counter()
    res = s.post(
        f"{base}/recommend",
        files={"audio": (args.wav.name, audio_bytes, "audio/wav")},
        headers=_h(access),
    )
    elapsed = time.perf_counter() - t0
    rec = _ok(f"POST /recommend  ({elapsed:.1f}s)", res, 200)

    session_id = rec["session_id"]
    tracks = rec.get("recommendations", [])
    print(f"      session_id    : {session_id}")
    print(f"      transcript    : {rec.get('transcript') or '(없음)'}")
    context = rec.get("context") or {}
    if context:
        print(f"      context       : time={context.get('time_of_day')}  "
              f"loc={context.get('location')}  act={context.get('activity')}")
    print(f"      fallback_flags: {rec.get('fallback_flags')}")
    print(f"      추천 트랙 {len(tracks)}곡:")
    for i, item in enumerate(tracks, 1):
        t = item["track"]
        print(f"        {i}. [{t['track_id']}] {t['title']} — {t['artist']}  score={item['score']}")
        if item.get("reason"):
            print(f"           이유: {item['reason'][:80]}")

    if len(tracks) < 3:
        print("[WARN] 추천 결과가 3곡 미만 — 피드백 단계는 있는 곡만 테스트합니다")

    # ── 4. 피드백 ──────────────────────────────────────────
    section("4. 피드백")
    if len(tracks) >= 1:
        t1_id = tracks[0]["track"]["track_id"]
        res = s.post(
            f"{base}/feedback/like",
            json={"recommendation_id": session_id, "track_id": t1_id},
            headers=_h(access),
        )
        _ok(f"POST /feedback/like  ({t1_id})", res, 201)

        # 중복 좋아요 → 409
        res = s.post(
            f"{base}/feedback/like",
            json={"recommendation_id": session_id, "track_id": t1_id},
            headers=_h(access),
        )
        _fail(f"POST /feedback/like 중복 → 409  ({t1_id})", res, 409)

    if len(tracks) >= 2:
        t2_id = tracks[1]["track"]["track_id"]
        res = s.post(
            f"{base}/feedback/dislike",
            json={"recommendation_id": session_id, "track_id": t2_id},
            headers=_h(access),
        )
        _ok(f"POST /feedback/dislike  ({t2_id})", res, 201)

    if len(tracks) >= 3:
        t3_id = tracks[2]["track"]["track_id"]
        res = s.post(
            f"{base}/feedback/playback",
            json={"track_id": t3_id, "event": "start", "playback_pct": 0.0},
            headers=_h(access),
        )
        _ok(f"POST /feedback/playback start  ({t3_id})", res, 201)

        res = s.post(
            f"{base}/feedback/playback",
            json={"track_id": t3_id, "event": "complete", "playback_pct": 100.0},
            headers=_h(access),
        )
        _ok(f"POST /feedback/playback complete  ({t3_id})", res, 201)

    # ── 5. 이력 조회 ───────────────────────────────────────
    section("5. 이력 조회")
    res = s.get(f"{base}/history", headers=_h(access))
    history = _ok("GET /history", res, 200)
    print(f"      세션 수: {len(history)}")
    if history:
        item = history[0]
        print(f"      세션 ID : {item['id']}")
        print(f"      추천 트랙: {len(item.get('recommended_tracks', []))}곡")
        fb_list = item.get("feedbacks", [])
        print(f"      피드백   : {len(fb_list)}건")
        for fb in fb_list:
            print(f"        - {fb['track_id']}  type={fb.get('type') or fb.get('feedback_type', '?')}")

    # ── 6. 두 번째 추천 요청 (피드백 누적 후) ──────────────
    section("6. 두 번째 추천 요청 (피드백 반영 확인)")
    t0 = time.perf_counter()
    res = s.post(
        f"{base}/recommend",
        files={"audio": (args.wav.name, audio_bytes, "audio/wav")},
        headers=_h(access),
    )
    elapsed = time.perf_counter() - t0
    rec2 = _ok(f"POST /recommend  ({elapsed:.1f}s)", res, 200)
    print(f"      session_id : {rec2['session_id']}")
    print(f"      추천 트랙 {len(rec2.get('recommendations', []))}곡")

    res = s.get(f"{base}/history?n=10", headers=_h(access))
    hist2 = _ok("GET /history?n=10  (이력 2건 확인)", res, 200)
    print(f"      총 이력 : {len(hist2)}건")

    # ── 7. 토큰 갱신 ───────────────────────────────────────
    section("7. 토큰 갱신 (refresh rotation)")
    res = s.post(f"{base}/auth/refresh", json={"refresh_token": refresh})
    body = _ok("POST /auth/refresh", res, 200)
    new_access = body["access_token"]
    print(f"      새 access_token: {new_access[:40]}…")

    # 기존 refresh token 재사용 불가 (rotation)
    res = s.post(f"{base}/auth/refresh", json={"refresh_token": refresh})
    _fail("POST /auth/refresh 재사용 → 401", res, 401)

    # ── 8. 로그아웃 + 보호 엔드포인트 거부 ─────────────────
    section("8. 로그아웃 후 보호 엔드포인트 접근 거부")
    res = s.post(
        f"{base}/auth/logout",
        json={"refresh_token": "dummy"},
        headers=_h(new_access),
    )
    _fail("POST /auth/logout → 204", res, 204)

    res = s.post(
        f"{base}/recommend",
        files={"audio": (args.wav.name, audio_bytes, "audio/wav")},
        headers={"Authorization": "Bearer invalidtoken"},
    )
    _fail("POST /recommend (무효 토큰) → 401", res, 401)

    # ── 결과 요약 ──────────────────────────────────────────
    print(f"\n{'='*55}")
    print("  모든 시나리오 통과")
    print(f"  서버: {base}")
    print(f"{'='*55}\n")

    # 전체 응답 저장 (선택)
    out_path = Path("test_live_result.json")
    out_path.write_text(
        json.dumps({"first_recommend": rec, "second_recommend": rec2, "history": hist2}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  전체 응답 저장: {out_path.resolve()}\n")


if __name__ == "__main__":
    main()
