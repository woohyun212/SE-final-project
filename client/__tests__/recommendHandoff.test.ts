/**
 * sessionStorage 핸드오프 + toRecommendResult 미커버 분기 테스트 (#114 보강).
 *
 * 커버 대상:
 *  - saveRecommendResult / loadRecommendResult / clearRecommendResult (jsdom sessionStorage)
 *  - SSR 가드 (window undefined 분기) — jest globals 조작으로 시뮬레이션
 *  - sessionStorage 접근 예외 (setItem/getItem/removeItem 던짐 → 조용히 무시)
 *  - toRecommendResult 미커버 분기:
 *      user_emotion 누락 시 NEUTRAL(0.5) 기본값
 *      session_id 가 string 이 아닐 때 sessionId === undefined
 *      recommendations 가 빈 배열
 *      context 에 null 필드 포함
 *      fallback_flags 필드별 Boolean 강제 변환 (falsy 0 → false)
 */
import {
  saveRecommendResult,
  loadRecommendResult,
  clearRecommendResult,
  toRecommendResult,
  RecommendResult,
} from "../lib/recommend";

// ── 공통 픽스처 ─────────────────────────────────────────────────────────────

function makeResult(overrides: Partial<RecommendResult> = {}): RecommendResult {
  return {
    sessionId: "sess-abc",
    tracks: [
      {
        track_id: "t-1",
        title: "Hello",
        artist: "Artist",
        album: "Album",
        duration_sec: 200,
        preview_url: null,
        valence: 0.7,
        energy: 0.6,
        reason: null,
      },
    ],
    userEmotion: { valence: 0.4, energy: 0.5 },
    transcript: "테스트",
    context: null,
    ...overrides,
  };
}

// ── sessionStorage 핸드오프 ──────────────────────────────────────────────────

describe("saveRecommendResult / loadRecommendResult / clearRecommendResult", () => {
  const originalSessionStorage = window.sessionStorage;

  beforeEach(() => {
    // jsdom 은 sessionStorage 를 구현하므로 각 테스트 전에 초기화
    window.sessionStorage.clear();
  });

  it("저장 후 로드하면 동일 객체를 반환한다", () => {
    const result = makeResult();
    saveRecommendResult(result);
    expect(loadRecommendResult()).toEqual(result);
  });

  it("저장 전 로드하면 null 을 반환한다", () => {
    expect(loadRecommendResult()).toBeNull();
  });

  it("clear 후 로드하면 null 을 반환한다", () => {
    saveRecommendResult(makeResult());
    clearRecommendResult();
    expect(loadRecommendResult()).toBeNull();
  });

  it("같은 키로 덮어쓰면 최신값만 남는다", () => {
    const first = makeResult({ sessionId: "old" });
    const second = makeResult({ sessionId: "new" });
    saveRecommendResult(first);
    saveRecommendResult(second);
    expect(loadRecommendResult()?.sessionId).toBe("new");
  });

  it("sessionStorage 에 손상된 JSON 이 있으면 loadRecommendResult 는 null 을 반환한다", () => {
    window.sessionStorage.setItem("se_emotion_music__recommend_result", "{broken json");
    expect(loadRecommendResult()).toBeNull();
  });

  it("sessionStorage.setItem 이 예외를 던져도 saveRecommendResult 는 조용히 무시한다", () => {
    const throwing: Storage = {
      length: 0,
      key: () => null,
      getItem: () => null,
      setItem: () => { throw new DOMException("QuotaExceededError"); },
      removeItem: () => {},
      clear: () => {},
    };
    Object.defineProperty(window, "sessionStorage", { value: throwing, configurable: true });
    expect(() => saveRecommendResult(makeResult())).not.toThrow();
    // restore
    Object.defineProperty(window, "sessionStorage", { value: originalSessionStorage, configurable: true });
  });

  it("sessionStorage.getItem 이 예외를 던져도 loadRecommendResult 는 null 을 반환한다", () => {
    const throwing: Storage = {
      length: 0,
      key: () => null,
      getItem: () => { throw new DOMException("SecurityError"); },
      setItem: () => {},
      removeItem: () => {},
      clear: () => {},
    };
    Object.defineProperty(window, "sessionStorage", { value: throwing, configurable: true });
    expect(loadRecommendResult()).toBeNull();
    Object.defineProperty(window, "sessionStorage", { value: originalSessionStorage, configurable: true });
  });

  it("sessionStorage.removeItem 이 예외를 던져도 clearRecommendResult 는 조용히 무시한다", () => {
    const throwing: Storage = {
      length: 0,
      key: () => null,
      getItem: () => null,
      setItem: () => {},
      removeItem: () => { throw new DOMException("SecurityError"); },
      clear: () => {},
    };
    Object.defineProperty(window, "sessionStorage", { value: throwing, configurable: true });
    expect(() => clearRecommendResult()).not.toThrow();
    Object.defineProperty(window, "sessionStorage", { value: originalSessionStorage, configurable: true });
  });
});

// ── SSR 가드 (window === undefined 분기) ────────────────────────────────────

describe("SSR 가드 — window 가 undefined 일 때", () => {
  let originalWindow: typeof globalThis.window;

  beforeEach(() => {
    originalWindow = global.window;
    // @ts-expect-error: SSR 환경 시뮬레이션
    delete global.window;
  });

  afterEach(() => {
    global.window = originalWindow;
  });

  it("saveRecommendResult 는 아무 작업 없이 반환한다", () => {
    expect(() => saveRecommendResult(makeResult())).not.toThrow();
  });

  it("loadRecommendResult 는 null 을 반환한다", () => {
    expect(loadRecommendResult()).toBeNull();
  });

  it("clearRecommendResult 는 아무 작업 없이 반환한다", () => {
    expect(() => clearRecommendResult()).not.toThrow();
  });
});

// ── toRecommendResult 미커버 분기 ───────────────────────────────────────────

describe("toRecommendResult — 미커버 분기 보강", () => {
  it("user_emotion 이 누락되면 userEmotion 은 NEUTRAL(0.5, 0.5) 이다", () => {
    const raw = {
      recommendations: [
        {
          track: {
            track_id: "t-n",
            title: "No Emotion",
            artist: "A",
            album: "B",
            duration_sec: 180,
          },
          score: 0.5,
          track_features: { valence: 0.5, energy: 0.5 },
        },
      ],
      // user_emotion 필드 없음
    };
    const result = toRecommendResult(raw);
    expect(result.userEmotion).toEqual({ valence: 0.5, energy: 0.5 });
  });

  it("session_id 가 숫자이면 sessionId 는 undefined 이다", () => {
    const raw = {
      session_id: 12345, // string 이 아님
      recommendations: [
        {
          track: {
            track_id: "t-x",
            title: "X",
            artist: "A",
            album: "B",
            duration_sec: 200,
          },
          score: 0.8,
          track_features: { valence: 0.6, energy: 0.6 },
        },
      ],
      user_emotion: { valence: 0.5, energy: 0.5 },
    };
    expect(toRecommendResult(raw).sessionId).toBeUndefined();
  });

  it("session_id 가 없으면 sessionId 는 undefined 이다", () => {
    const raw = {
      recommendations: [
        {
          track: {
            track_id: "t-y",
            title: "Y",
            artist: "A",
            album: "B",
            duration_sec: 200,
          },
          score: 0.7,
          track_features: { valence: 0.4, energy: 0.4 },
        },
      ],
      user_emotion: { valence: 0.4, energy: 0.4 },
    };
    expect(toRecommendResult(raw).sessionId).toBeUndefined();
  });

  it("recommendations 가 빈 배열이면 tracks 는 [] 이다", () => {
    const raw = {
      session_id: "sess-empty",
      recommendations: [],
      user_emotion: { valence: 0.5, energy: 0.5 },
    };
    const result = toRecommendResult(raw);
    expect(result.tracks).toEqual([]);
    expect(result.sessionId).toBe("sess-empty");
    expect(result.userEmotion).toEqual({ valence: 0.5, energy: 0.5 });
  });

  it("context 의 일부 필드가 null 이면 그대로 null 을 유지한다", () => {
    const raw = {
      recommendations: [
        {
          track: {
            track_id: "t-ctx",
            title: "Ctx",
            artist: "A",
            album: "B",
            duration_sec: 200,
          },
          score: 0.6,
          track_features: { valence: 0.5, energy: 0.5 },
        },
      ],
      user_emotion: { valence: 0.5, energy: 0.5 },
      context: {
        time_of_day: null,
        location: null,
        activity: "running",
        emotions: null,
      },
    };
    const result = toRecommendResult(raw);
    expect(result.context).toEqual({
      time_of_day: null,
      location: null,
      activity: "running",
      emotions: null,
    });
  });

  it("fallback_flags 의 falsy 숫자값(0)은 false 로 변환된다", () => {
    const raw = {
      recommendations: [
        {
          track: {
            track_id: "t-ff",
            title: "FF",
            artist: "A",
            album: "B",
            duration_sec: 200,
          },
          score: 0.5,
          track_features: { valence: 0.5, energy: 0.5 },
        },
      ],
      user_emotion: { valence: 0.5, energy: 0.5 },
      fallback_flags: { ml: 0, context: 1, reason: 0 },
    };
    const result = toRecommendResult(raw);
    expect(result.fallbackFlags).toEqual({ ml: false, context: true, reason: false });
  });

  it("알 수 없는 shape 의 빈 결과는 NEUTRAL userEmotion 을 반환한다", () => {
    const result = toRecommendResult({ foo: "bar" });
    expect(result.tracks).toEqual([]);
    expect(result.userEmotion).toEqual({ valence: 0.5, energy: 0.5 });
    expect(result.transcript).toBeNull();
  });
});
