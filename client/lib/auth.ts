import type { TokenResponse, AccessTokenResponse } from "./api";

// ── Storage keys ───────────────────────────────────────────────────────────

const KEY_ACCESS_TOKEN = "se_emotion_music__access_token";
const KEY_REFRESH_TOKEN = "se_emotion_music__refresh_token";

// ── Helpers ────────────────────────────────────────────────────────────────

/** Returns false when running in a non-browser environment (SSR / Node.js). */
function hasWindow(): boolean {
  return typeof window !== "undefined";
}

function storageGet(key: string): string | null {
  if (!hasWindow()) return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    // localStorage may throw in restricted environments (e.g. sandboxed
    // Electron renderer with storage access blocked).
    return null;
  }
}

function storageSet(key: string, value: string): void {
  if (!hasWindow()) return;
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Silently ignore — caller proceeds without persisting the token.
  }
}

function storageRemove(key: string): void {
  if (!hasWindow()) return;
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Silently ignore.
  }
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Persists both access and refresh tokens returned after login / signup.
 *
 * TODO (PR #67 품질 4): `tokens.token_type` 은 현재 저장하지 않는다 — 백엔드가 항상
 * "bearer" 를 반환하고 authedFetch 도 동일 가정하기 때문. 향후 다중 스킴(예: DPoP,
 * MAC) 지원이 필요해지면 token_type 도 함께 저장하고 헤더 생성 시 사용해야 함.
 */
export function saveTokens(tokens: TokenResponse): void {
  storageSet(KEY_ACCESS_TOKEN, tokens.access_token);
  storageSet(KEY_REFRESH_TOKEN, tokens.refresh_token);
}

/**
 * Updates only the access token (used after a token refresh).
 *
 * TODO (PR #67 품질 4): saveTokens 와 동일 — `token.token_type` 미사용.
 */
export function saveAccessToken(token: AccessTokenResponse): void {
  storageSet(KEY_ACCESS_TOKEN, token.access_token);
}

/** Returns the stored access token, or `null` if absent / unavailable. */
export function getAccessToken(): string | null {
  return storageGet(KEY_ACCESS_TOKEN);
}

/** Returns the stored refresh token, or `null` if absent / unavailable. */
export function getRefreshToken(): string | null {
  return storageGet(KEY_REFRESH_TOKEN);
}

/** Removes both tokens from storage (i.e. logs the user out locally). */
export function clearTokens(): void {
  storageRemove(KEY_ACCESS_TOKEN);
  storageRemove(KEY_REFRESH_TOKEN);
}

/**
 * Returns `true` when an access token is present in storage.
 * Does NOT verify expiry — purely a presence check.
 */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

// ── JWT expiry ─────────────────────────────────────────────────────────────

/**
 * JWT 페이로드에서 exp (Unix epoch seconds) 를 추출. 디코드 실패 시 null.
 * 서명 검증 안 함 — 단순 base64url 디코드 + JSON parse.
 */
export function getAccessTokenExpiry(): number | null {
  if (!hasWindow()) return null;
  const token = getAccessToken();
  if (!token) return null;

  const parts = token.split(".");
  if (parts.length !== 3) return null;

  try {
    // base64url → base64
    const base64 = parts[1]
      .replace(/-/g, "+")
      .replace(/_/g, "/")
      .padEnd(parts[1].length + ((4 - (parts[1].length % 4)) % 4), "=");

    const payload: unknown = JSON.parse(atob(base64));

    if (
      payload !== null &&
      typeof payload === "object" &&
      "exp" in payload &&
      typeof (payload as { exp: unknown }).exp === "number"
    ) {
      return (payload as { exp: number }).exp;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * 현재 액세스 토큰이 만료됐는지 (또는 만료 임박 — leeway 초 이내).
 * @param leewaySeconds 기본 30 — 만료 30초 전부터 만료로 간주 (자동 refresh 트리거용)
 */
export function isAccessTokenExpired(leewaySeconds = 30): boolean {
  const exp = getAccessTokenExpiry();
  if (exp === null) return true; // 토큰 없거나 디코드 실패 → 만료로 간주
  return Date.now() / 1000 >= exp - leewaySeconds;
}

// ── Auto-refresh ───────────────────────────────────────────────────────────

/**
 * 현재 access_token 이 만료(또는 임박)면 refresh_token 으로 새 access_token 발급 시도.
 * 성공 시 saveAccessToken 으로 저장.
 * 실패 (refresh 토큰 만료/없음) 시 clearTokens 후 throw.
 *
 * @param force `true` 면 만료 검사 없이 강제로 refresh 호출. authedFetch 가 서버
 *   401 응답을 받았을 때 (서버측 토큰 무효화 / 시계 편차 등으로 로컬 만료 검사가
 *   현실과 어긋난 상황) 새 토큰을 얻기 위해 사용.
 * @returns 새로운 access_token 또는 기존 유효한 access_token. 인증 안 됨이면 null.
 */
export async function ensureFreshAccessToken(
  force = false,
): Promise<string | null> {
  const current = getAccessToken();
  if (!current) return null;

  if (!force && !isAccessTokenExpired()) return current;

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearTokens();
    return null;
  }

  try {
    // circular dependency 회피를 위한 dynamic import
    const { refreshApi } = await import("./api");
    const response = await refreshApi(refreshToken);
    saveAccessToken(response);
    return response.access_token;
  } catch (err) {
    clearTokens();
    throw err;
  }
}

// ── Logout ─────────────────────────────────────────────────────────────────

/**
 * 로그아웃 — localStorage 토큰 모두 제거. (라우팅은 호출자가 router.push)
 */
export function logout(): void {
  clearTokens();
}
