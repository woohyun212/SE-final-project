/**
 * logoutApi 단위 테스트.
 * authedFetch 경유(Bearer 첨부) + snake_case body + 엔드포인트/메서드 검증.
 */
import { logoutApi } from "../lib/api";
import { saveTokens } from "../lib/auth";

const realFetch = global.fetch;

function mockNoContent() {
  return jest.fn().mockResolvedValue({
    ok: true,
    status: 204,
    json: async () => {
      throw new Error("no body");
    },
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

describe("logoutApi", () => {
  it("POST /auth/logout + snake_case body + Bearer 헤더", async () => {
    const f = mockNoContent();
    global.fetch = f as unknown as typeof fetch;

    await logoutApi("ref");

    const [url, init] = f.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/auth\/logout$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ refresh_token: "ref" });
    expect((init.headers as Record<string, string>).Authorization).toBe(
      "Bearer tok"
    );
  });

  it("204 응답 시 void 반환 (json 파싱 없음)", async () => {
    const f = mockNoContent();
    global.fetch = f as unknown as typeof fetch;

    const result = await logoutApi("ref");

    expect(result).toBeUndefined();
  });
});
