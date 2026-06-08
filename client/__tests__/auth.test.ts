/**
 * auth.ts 단위 테스트.
 * localStorage(jsdom) 사용, JWT exp 디코딩·만료 판정·refresh 경로(fetch mock)·실패 시 클리어.
 */
import {
  saveTokens,
  saveAccessToken,
  getAccessToken,
  getRefreshToken,
  clearTokens,
  isAuthenticated,
  getAccessTokenExpiry,
  isAccessTokenExpired,
  ensureFreshAccessToken,
  logout,
} from "../lib/auth";

// ── JWT helpers ─────────────────────────────────────────────────────────────

function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `${header}.${body}.signature`;
}

const FUTURE_EXP = Math.floor(Date.now() / 1000) + 3600; // 1시간 후
const PAST_EXP = Math.floor(Date.now() / 1000) - 3600;   // 1시간 전

const realFetch = global.fetch;

afterEach(() => {
  global.fetch = realFetch;
  window.localStorage.clear();
  jest.clearAllMocks();
  jest.restoreAllMocks();
});

// ── saveTokens ──────────────────────────────────────────────────────────────

describe("saveTokens", () => {
  it("access_token 과 refresh_token 을 localStorage 에 저장한다", () => {
    saveTokens({ access_token: "acc", refresh_token: "ref", token_type: "bearer" });
    expect(window.localStorage.getItem("se_emotion_music__access_token")).toBe("acc");
    expect(window.localStorage.getItem("se_emotion_music__refresh_token")).toBe("ref");
  });
});

// ── saveAccessToken ─────────────────────────────────────────────────────────

describe("saveAccessToken", () => {
  it("access_token 만 갱신하고 refresh_token 은 건드리지 않는다", () => {
    saveTokens({ access_token: "old_acc", refresh_token: "ref", token_type: "bearer" });
    saveAccessToken({ access_token: "new_acc", token_type: "bearer" });
    expect(window.localStorage.getItem("se_emotion_music__access_token")).toBe("new_acc");
    expect(window.localStorage.getItem("se_emotion_music__refresh_token")).toBe("ref");
  });
});

// ── getAccessToken ──────────────────────────────────────────────────────────

describe("getAccessToken", () => {
  it("저장된 access_token 을 반환한다", () => {
    saveTokens({ access_token: "tok", refresh_token: "ref", token_type: "bearer" });
    expect(getAccessToken()).toBe("tok");
  });

  it("토큰 없으면 null 반환", () => {
    expect(getAccessToken()).toBeNull();
  });
});

// ── getRefreshToken ─────────────────────────────────────────────────────────

describe("getRefreshToken", () => {
  it("저장된 refresh_token 을 반환한다", () => {
    saveTokens({ access_token: "acc", refresh_token: "ref123", token_type: "bearer" });
    expect(getRefreshToken()).toBe("ref123");
  });

  it("토큰 없으면 null 반환", () => {
    expect(getRefreshToken()).toBeNull();
  });
});

// ── clearTokens ─────────────────────────────────────────────────────────────

describe("clearTokens", () => {
  it("access_token 과 refresh_token 을 모두 제거한다", () => {
    saveTokens({ access_token: "acc", refresh_token: "ref", token_type: "bearer" });
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});

// ── isAuthenticated ─────────────────────────────────────────────────────────

describe("isAuthenticated", () => {
  it("access_token 존재 시 true 반환", () => {
    saveTokens({ access_token: "tok", refresh_token: "ref", token_type: "bearer" });
    expect(isAuthenticated()).toBe(true);
  });

  it("access_token 없으면 false 반환", () => {
    expect(isAuthenticated()).toBe(false);
  });

  it("clearTokens 후 false 반환", () => {
    saveTokens({ access_token: "tok", refresh_token: "ref", token_type: "bearer" });
    clearTokens();
    expect(isAuthenticated()).toBe(false);
  });
});

// ── logout ──────────────────────────────────────────────────────────────────

describe("logout", () => {
  it("두 토큰 모두 제거한다", () => {
    saveTokens({ access_token: "acc", refresh_token: "ref", token_type: "bearer" });
    logout();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});

// ── getAccessTokenExpiry ────────────────────────────────────────────────────

describe("getAccessTokenExpiry", () => {
  it("유효한 JWT 의 exp 를 반환한다", () => {
    const jwt = makeJwt({ exp: FUTURE_EXP, sub: "user1" });
    saveTokens({ access_token: jwt, refresh_token: "ref", token_type: "bearer" });
    expect(getAccessTokenExpiry()).toBe(FUTURE_EXP);
  });

  it("토큰 없으면 null 반환", () => {
    expect(getAccessTokenExpiry()).toBeNull();
  });

  it("JWT 형식이 아니면 null 반환 (파트 수 != 3)", () => {
    saveTokens({ access_token: "not.a.valid.jwt.here", refresh_token: "ref", token_type: "bearer" });
    expect(getAccessTokenExpiry()).toBeNull();
  });

  it("페이로드에 exp 없으면 null 반환", () => {
    const jwt = makeJwt({ sub: "user1" }); // exp 없음
    saveTokens({ access_token: jwt, refresh_token: "ref", token_type: "bearer" });
    expect(getAccessTokenExpiry()).toBeNull();
  });

  it("base64 디코드 실패 시 null 반환", () => {
    // 페이로드 부분이 유효하지 않은 base64
    saveTokens({ access_token: "header.!!!invalid!!!.sig", refresh_token: "ref", token_type: "bearer" });
    expect(getAccessTokenExpiry()).toBeNull();
  });

  it("exp 가 숫자 아닌 경우 null 반환", () => {
    const jwt = makeJwt({ exp: "not-a-number" });
    saveTokens({ access_token: jwt, refresh_token: "ref", token_type: "bearer" });
    expect(getAccessTokenExpiry()).toBeNull();
  });
});

// ── isAccessTokenExpired ────────────────────────────────────────────────────

describe("isAccessTokenExpired", () => {
  it("만료된 토큰은 true 반환", () => {
    const jwt = makeJwt({ exp: PAST_EXP });
    saveTokens({ access_token: jwt, refresh_token: "ref", token_type: "bearer" });
    expect(isAccessTokenExpired(0)).toBe(true);
  });

  it("유효한 토큰(leeway=0)은 false 반환", () => {
    const jwt = makeJwt({ exp: FUTURE_EXP });
    saveTokens({ access_token: jwt, refresh_token: "ref", token_type: "bearer" });
    expect(isAccessTokenExpired(0)).toBe(false);
  });

  it("기본 leeway=30 — 30초 이내 만료 토큰은 만료로 간주", () => {
    const exp = Math.floor(Date.now() / 1000) + 10; // 10초 후 만료
    const jwt = makeJwt({ exp });
    saveTokens({ access_token: jwt, refresh_token: "ref", token_type: "bearer" });
    expect(isAccessTokenExpired()).toBe(true); // leeway=30 이므로 만료로 간주
  });

  it("토큰 없으면 true 반환", () => {
    expect(isAccessTokenExpired()).toBe(true);
  });

  it("JWT 파싱 불가 시 true 반환", () => {
    saveTokens({ access_token: "bad-token", refresh_token: "ref", token_type: "bearer" });
    expect(isAccessTokenExpired()).toBe(true);
  });
});

// ── ensureFreshAccessToken ──────────────────────────────────────────────────

describe("ensureFreshAccessToken", () => {
  it("토큰 없으면 null 반환", async () => {
    const result = await ensureFreshAccessToken();
    expect(result).toBeNull();
  });

  it("만료되지 않은 토큰이면 그대로 반환 (fetch 호출 없음)", async () => {
    const jwt = makeJwt({ exp: FUTURE_EXP });
    saveTokens({ access_token: jwt, refresh_token: "ref", token_type: "bearer" });
    const f = jest.fn();
    global.fetch = f as unknown as typeof fetch;

    const result = await ensureFreshAccessToken();

    expect(result).toBe(jwt);
    expect(f).not.toHaveBeenCalled();
  });

  it("만료된 토큰 + refresh 성공 → 새 access_token 저장 후 반환", async () => {
    const expiredJwt = makeJwt({ exp: PAST_EXP });
    saveTokens({ access_token: expiredJwt, refresh_token: "ref-tok", token_type: "bearer" });

    const newAccessToken = makeJwt({ exp: FUTURE_EXP });
    const f = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: newAccessToken, token_type: "bearer" }),
    });
    global.fetch = f as unknown as typeof fetch;

    const result = await ensureFreshAccessToken();

    expect(result).toBe(newAccessToken);
    expect(getAccessToken()).toBe(newAccessToken);
    // refresh_token 은 유지
    expect(getRefreshToken()).toBe("ref-tok");
  });

  it("force=true 이면 만료 여부 무관하게 refresh 호출", async () => {
    const validJwt = makeJwt({ exp: FUTURE_EXP });
    saveTokens({ access_token: validJwt, refresh_token: "ref-tok", token_type: "bearer" });

    const newAccessToken = makeJwt({ exp: FUTURE_EXP + 3600 });
    const f = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: newAccessToken, token_type: "bearer" }),
    });
    global.fetch = f as unknown as typeof fetch;

    const result = await ensureFreshAccessToken(true);

    expect(f).toHaveBeenCalled();
    expect(result).toBe(newAccessToken);
  });

  it("refresh_token 없으면 clearTokens 후 null 반환", async () => {
    const expiredJwt = makeJwt({ exp: PAST_EXP });
    // refresh_token 없이 access_token 만 저장
    window.localStorage.setItem("se_emotion_music__access_token", expiredJwt);

    const result = await ensureFreshAccessToken();

    expect(result).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it("refresh API 실패 시 clearTokens 후 throw", async () => {
    const expiredJwt = makeJwt({ exp: PAST_EXP });
    saveTokens({ access_token: expiredJwt, refresh_token: "bad-ref", token_type: "bearer" });

    const f = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Refresh token expired" }),
    });
    global.fetch = f as unknown as typeof fetch;

    await expect(ensureFreshAccessToken()).rejects.toThrow();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("refresh fetch 자체가 reject 되면 clearTokens 후 throw", async () => {
    const expiredJwt = makeJwt({ exp: PAST_EXP });
    saveTokens({ access_token: expiredJwt, refresh_token: "ref-tok", token_type: "bearer" });

    const f = jest.fn().mockRejectedValue(new Error("Network error"));
    global.fetch = f as unknown as typeof fetch;

    await expect(ensureFreshAccessToken()).rejects.toThrow();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});
