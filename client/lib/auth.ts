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

/** Persists both access and refresh tokens returned after login / signup. */
export function saveTokens(tokens: TokenResponse): void {
  storageSet(KEY_ACCESS_TOKEN, tokens.access_token);
  storageSet(KEY_REFRESH_TOKEN, tokens.refresh_token);
}

/** Updates only the access token (used after a token refresh). */
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
