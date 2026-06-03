/**
 * feedbackApi / playbackApi / historyApi 단위 테스트 (#47/#48/#50 Foundation).
 * authedFetch 경유(Bearer 첨부) + snake_case body + 엔드포인트/메서드 검증.
 */
import { feedbackApi, playbackApi, historyApi } from "../lib/api";
import { saveTokens } from "../lib/auth";

const realFetch = global.fetch;

function mockOk(json: unknown = {}) {
  return jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => json,
  });
}

beforeEach(() => {
  saveTokens({
    access_token: "tok",
    refresh_token: "ref",
    token_type: "bearer",
  });
});

afterEach(() => {
  global.fetch = realFetch;
  window.localStorage.clear();
  jest.clearAllMocks();
});

describe("feedbackApi", () => {
  it("like → POST /feedback/like + snake_case body + Bearer", async () => {
    const f = mockOk();
    global.fetch = f as unknown as typeof fetch;

    await feedbackApi("like", "t-1", "sess-1");

    const [url, init] = f.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/feedback\/like$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({
      track_id: "t-1",
      recommendation_id: "sess-1",
    });
    expect((init.headers as Record<string, string>).Authorization).toBe(
      "Bearer tok"
    );
  });

  it("dislike → POST /feedback/dislike", async () => {
    const f = mockOk();
    global.fetch = f as unknown as typeof fetch;

    await feedbackApi("dislike", "t-2", "sess-2");

    expect((f.mock.calls[0] as [string])[0]).toMatch(/\/feedback\/dislike$/);
  });
});

describe("playbackApi", () => {
  it("playback_pct 포함 시 body 에 추가", async () => {
    const f = mockOk();
    global.fetch = f as unknown as typeof fetch;

    await playbackApi("t-1", "complete", 100);

    const [url, init] = f.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/feedback\/playback$/);
    expect(JSON.parse(init.body as string)).toEqual({
      track_id: "t-1",
      event: "complete",
      playback_pct: 100,
    });
  });

  it("playback_pct 생략 시 body 에서 제외", async () => {
    const f = mockOk();
    global.fetch = f as unknown as typeof fetch;

    await playbackApi("t-1", "start");

    expect(JSON.parse((f.mock.calls[0] as [string, RequestInit])[1].body as string)).toEqual({
      track_id: "t-1",
      event: "start",
    });
  });
});

describe("historyApi", () => {
  it("n 쿼리 + GET /history + 응답 반환", async () => {
    const items = [
      {
        id: "h1",
        user_valence: 0.5,
        user_energy: 0.5,
        created_at: "2026-06-03",
        recommended_tracks: [],
        feedbacks: [],
      },
    ];
    const f = mockOk(items);
    global.fetch = f as unknown as typeof fetch;

    const res = await historyApi(10);

    const [url, init] = f.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/history\?n=10$/);
    expect(init.method).toBe("GET");
    expect(res).toEqual(items);
  });

  it("n 생략 시 쿼리 없음", async () => {
    const f = mockOk([]);
    global.fetch = f as unknown as typeof fetch;

    await historyApi();

    expect((f.mock.calls[0] as [string])[0]).toMatch(/\/history$/);
  });
});
