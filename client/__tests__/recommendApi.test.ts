/**
 * recommendApi 단위 테스트 (US-3 / 이슈 #18).
 *
 * multipart/form-data 로 audio 필드를 전송하고, Content-Type 을 직접 지정하지 않으며
 * (브라우저가 boundary 설정), 저장된 access token 을 Bearer 로 첨부하는지 검증.
 */
import { ApiError, recommendApi } from "../lib/api";
import { saveTokens } from "../lib/auth";

const realFetch = global.fetch;

afterEach(() => {
  global.fetch = realFetch;
  window.localStorage.clear();
  jest.clearAllMocks();
});

describe("recommendApi", () => {
  it("POST /recommend 로 audio FormData 를 Bearer 와 함께 전송", async () => {
    saveTokens({
      access_token: "tok-123",
      refresh_token: "ref-123",
      token_type: "bearer",
    });

    // jsdom 에는 Response 생성자가 없으므로 apiFetch 가 쓰는 인터페이스
    // (ok / status / json) 만 갖춘 가짜 응답을 반환한다.
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ tracks: [] }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const blob = new Blob(["audio"], { type: "audio/webm" });
    const res = await recommendApi(blob);

    expect(res).toEqual({ tracks: [] });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/recommend$/);
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("audio")).toBeInstanceOf(Blob);

    const headers = init.headers as Record<string, string>;
    // multipart 본문에는 application/json 을 강제하지 않는다.
    expect(headers["Content-Type"]).toBeUndefined();
    expect(headers.Authorization).toBe("Bearer tok-123");
  });

  it("비-2xx 응답은 ApiError 로 throw", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: "분석 실패" }),
    }) as unknown as typeof fetch;

    await expect(recommendApi(new Blob(["x"]))).rejects.toBeInstanceOf(ApiError);
  });
});
