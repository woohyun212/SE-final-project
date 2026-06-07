/**
 * toRecommendResult 어댑터 단위 테스트 (#114).
 *
 * 백엔드 /recommend 확정 응답(snake_case·중첩)을 도메인 RecommendResult 로
 * 변환하는 단일 경계를 검증. 확정 shape(recommendations / track_features /
 * session_id / context / fallback_flags) 매핑 + 선택 필드 기본값 + 빈 입력을 커버한다.
 */
import { toRecommendResult } from "../lib/recommend";

describe("toRecommendResult", () => {
  it("새 shape(recommendations + track_features + user_emotion)을 매핑한다", () => {
    const raw = {
      session_id: "sess-1",
      recommendations: [
        {
          track: {
            track_id: "t-1",
            title: "Sunrise",
            artist: "Lumio",
            album: "Daybreak",
            duration_sec: 213,
            preview_url: "https://example.com/p.mp3",
          },
          score: 0.92,
          reason: "밝고 경쾌한 곡",
          track_features: { valence: 0.86, energy: 0.81 },
        },
      ],
      user_emotion: { valence: 0.38, energy: 0.62 },
      transcript: "오늘 좋았어",
    };

    const result = toRecommendResult(raw);

    expect(result.tracks).toHaveLength(1);
    const t = result.tracks[0];
    expect(t.track_id).toBe("t-1");
    expect(t.title).toBe("Sunrise");
    expect(t.preview_url).toBe("https://example.com/p.mp3");
    // track_features → flat valence/energy
    expect(t.valence).toBe(0.86);
    expect(t.energy).toBe(0.81);
    expect(t.reason).toBe("밝고 경쾌한 곡");
    // user_emotion → userEmotion
    expect(result.userEmotion).toEqual({ valence: 0.38, energy: 0.62 });
    expect(result.transcript).toBe("오늘 좋았어");
    // session_id → sessionId (피드백 API 연동 키, #47)
    expect(result.sessionId).toBe("sess-1");
  });

  it("reason / preview_url 누락 시 null 로 채운다", () => {
    const raw = {
      session_id: "sess-2",
      recommendations: [
        {
          track: {
            track_id: "t-2",
            title: "Quiet",
            artist: "Pine",
            album: "Still",
            duration_sec: 247,
          },
          score: 0.7,
          track_features: { valence: 0.78, energy: 0.27 },
        },
      ],
      user_emotion: { valence: 0.4, energy: 0.5 },
    };

    const t = toRecommendResult(raw).tracks[0];
    expect(t.preview_url).toBeNull();
    expect(t.reason).toBeNull();
    expect(toRecommendResult(raw).transcript).toBeNull();
  });

  it("context 필드가 있으면 ContextResult 로 매핑한다", () => {
    const raw = {
      session_id: "sess-3",
      recommendations: [
        {
          track: {
            track_id: "t-3",
            title: "Morning",
            artist: "A",
            album: "B",
            duration_sec: 180,
          },
          score: 0.8,
          track_features: { valence: 0.6, energy: 0.5 },
        },
      ],
      user_emotion: { valence: 0.5, energy: 0.5 },
      context: {
        time_of_day: "morning",
        location: "home",
        activity: "studying",
        emotions: { happy: 0.6, calm: 0.3 },
      },
    };

    const result = toRecommendResult(raw);
    expect(result.context).toEqual({
      time_of_day: "morning",
      location: "home",
      activity: "studying",
      emotions: { happy: 0.6, calm: 0.3 },
    });
  });

  it("context 필드 없으면 null 을 반환한다", () => {
    const raw = {
      session_id: "sess-4",
      recommendations: [
        {
          track: {
            track_id: "t-4",
            title: "Evening",
            artist: "B",
            album: "C",
            duration_sec: 200,
          },
          score: 0.75,
          track_features: { valence: 0.4, energy: 0.3 },
        },
      ],
      user_emotion: { valence: 0.4, energy: 0.3 },
    };

    const result = toRecommendResult(raw);
    expect(result.context).toBeNull();
  });

  it("fallback_flags 가 있으면 FallbackFlags 로 매핑한다", () => {
    const raw = {
      session_id: "sess-5",
      recommendations: [
        {
          track: {
            track_id: "t-5",
            title: "Fallback",
            artist: "C",
            album: "D",
            duration_sec: 190,
          },
          score: 0.5,
          track_features: { valence: 0.5, energy: 0.5 },
        },
      ],
      user_emotion: { valence: 0.5, energy: 0.5 },
      fallback_flags: { ml: true, context: false, reason: true },
    };

    const result = toRecommendResult(raw);
    expect(result.fallbackFlags).toEqual({ ml: true, context: false, reason: true });
  });

  it("fallback_flags 없으면 undefined 를 반환한다", () => {
    const raw = {
      session_id: "sess-6",
      recommendations: [
        {
          track: {
            track_id: "t-6",
            title: "Normal",
            artist: "D",
            album: "E",
            duration_sec: 210,
          },
          score: 0.9,
          track_features: { valence: 0.7, energy: 0.6 },
        },
      ],
      user_emotion: { valence: 0.7, energy: 0.6 },
    };

    const result = toRecommendResult(raw);
    expect(result.fallbackFlags).toBeUndefined();
  });

  it("알 수 없는/빈 입력은 빈 결과를 반환한다", () => {
    expect(toRecommendResult(null).tracks).toEqual([]);
    expect(toRecommendResult(undefined).tracks).toEqual([]);
    expect(toRecommendResult({}).tracks).toEqual([]);
    expect(toRecommendResult({ foo: "bar" }).tracks).toEqual([]);
  });
});
