/**
 * toRecommendResult 어댑터 단위 테스트 (#114).
 *
 * 백엔드 /recommend 응답(raw, snake_case·중첩)을 도메인 RecommendResult 로
 * 변환하는 단일 경계를 검증. 백엔드 최종 schema(track_features / session_id)
 * 변경에 대응하는 매핑 + 옛 shape fallback + 빈 입력을 커버한다.
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

  it("옛 shape({ tracks })는 fallback 으로 중립값/null 매핑한다", () => {
    const raw = {
      tracks: [
        { title: "Old", artist: "A", album: "B", duration_sec: 200 },
      ],
    };

    const result = toRecommendResult(raw);
    expect(result.tracks).toHaveLength(1);
    const t = result.tracks[0];
    expect(t.title).toBe("Old");
    expect(t.track_id).toBe("legacy-0"); // track_id 미제공 → 합성
    expect(t.valence).toBe(0.5);
    expect(t.energy).toBe(0.5);
    expect(t.reason).toBeNull();
    expect(result.userEmotion).toEqual({ valence: 0.5, energy: 0.5 });
  });

  it("알 수 없는/빈 입력은 빈 결과를 반환한다", () => {
    expect(toRecommendResult(null).tracks).toEqual([]);
    expect(toRecommendResult(undefined).tracks).toEqual([]);
    expect(toRecommendResult({}).tracks).toEqual([]);
    expect(toRecommendResult({ foo: "bar" }).tracks).toEqual([]);
  });
});
