/**
 * recommendApi 단위 테스트 (US-3 / 이슈 #18).
 *
 * multipart/form-data 로 audio 필드를 전송하고, Content-Type 을 직접 지정하지 않으며
 * (브라우저가 boundary 설정), 저장된 access token 을 Bearer 로 첨부하는지 검증.
 */
import { ApiError, recommendApi } from "../lib/api";
import { getAccessToken, saveTokens } from "../lib/auth";

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

  // ── 인증 필수화(#108 /recommend 에 get_current_user) 대응 경로 (#111) ──

  it("토큰이 없으면 Authorization 헤더를 첨부하지 않는다 (익명 호출 형태)", async () => {
    // localStorage 비어 있음 (afterEach 가 clear) — 미인증 상태.
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ tracks: [] }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    await recommendApi(new Blob(["audio"], { type: "audio/webm" }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("401 수신 시 refresh 후 같은 요청을 새 토큰으로 재시도해 성공한다", async () => {
    saveTokens({
      access_token: "old-tok",
      refresh_token: "ref-123",
      token_type: "bearer",
    });

    const fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ access_token: "new-tok", token_type: "bearer" }),
        });
      }
      // /recommend: 첫 호출(old-tok)은 401, 재시도(new-tok)는 200
      const recommendSoFar = fetchMock.mock.calls.filter((c: unknown[]) =>
        (c[0] as string).endsWith("/recommend")
      ).length;
      if (recommendSoFar === 1) {
        return Promise.resolve({
          ok: false,
          status: 401,
          json: async () => ({ detail: "토큰이 만료되었습니다." }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ tracks: [] }),
      });
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const res = await recommendApi(new Blob(["audio"]));
    expect(res).toEqual({ tracks: [] });

    const recommendCalls = fetchMock.mock.calls.filter((c) =>
      (c[0] as string).endsWith("/recommend")
    );
    const refreshCalls = fetchMock.mock.calls.filter((c) =>
      (c[0] as string).endsWith("/auth/refresh")
    );
    expect(recommendCalls).toHaveLength(2); // 401 → retry
    expect(refreshCalls).toHaveLength(1);

    // 재시도는 새 access token 으로
    const retryInit = recommendCalls[1][1] as RequestInit;
    const retryHeaders = retryInit.headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe("Bearer new-tok");
    expect(getAccessToken()).toBe("new-tok");
  });

  it("401 후 refresh 실패 시 ApiError(401) 를 던지고 저장된 토큰을 비운다", async () => {
    saveTokens({
      access_token: "old-tok",
      refresh_token: "bad-ref",
      token_type: "bearer",
    });

    const fetchMock = jest.fn().mockImplementation((url: string) => {
      // refresh 도 401 → refresh token 무효
      return Promise.resolve({
        ok: false,
        status: 401,
        json: async () =>
          url.endsWith("/auth/refresh")
            ? { detail: "refresh 토큰이 유효하지 않습니다." }
            : { detail: "토큰이 만료되었습니다." },
      });
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    await expect(recommendApi(new Blob(["x"]))).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
    });
    // refresh 실패 경로에서 clearTokens 가 호출되어 저장 토큰이 비워진다.
    expect(getAccessToken()).toBeNull();
  });
});
