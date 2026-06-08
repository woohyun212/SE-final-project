import type { FeedbackType, PlaybackEvent, HistoryItem } from "./recommend";

/**
 * API base URL 정규화 — 백엔드 TLS 적용 대응.
 *
 * 원격 호스트의 `http://` 는 `https://` 로 승격하고, 로컬 dev 호스트
 * (localhost/127.0.0.1/::1/*.local)는 그대로 둔다(로컬은 보통 TLS 미적용).
 * 사용자 `.env` 가 http 라도 런타임에 https 로 호출하도록 보장한다.
 * 말미 슬래시는 제거해 `${base}${path}` 결합 시 중복 슬래시를 막는다.
 */
export function normalizeApiBaseUrl(raw: string): string {
  const url = raw.trim().replace(/\/+$/, "");
  if (!url.startsWith("http://")) return url;

  const host = url.slice("http://".length).split("/")[0].split(":")[0];
  const isLocal =
    host === "localhost" ||
    host === "127.0.0.1" ||
    host === "::1" ||
    host.endsWith(".local");

  return isLocal ? url : `https://${url.slice("http://".length)}`;
}

const API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
);

// ── Types ──────────────────────────────────────────────────────────────────

export interface SignupRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

// 추천 응답의 도메인 타입은 client/lib/recommend.ts 의 RecommendResult 로 일원화되었다.
// recommendApi 는 raw 응답을 그대로 반환하고, 호출자가 toRecommendResult 로 변환한다
// (백엔드 응답 shape 변경을 어댑터 한 곳에서 흡수 — #114/#123).

// ── Error class ────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// ── Internal helpers ───────────────────────────────────────────────────────

/** Normalise a Pydantic 422 detail array to a single human-readable string. */
function normalisePydanticDetail(
  detail: Array<{ loc: unknown[]; msg: string; type: string }>
): string {
  if (detail.length === 0) return "입력 값이 올바르지 않습니다.";
  return detail[0].msg;
}

/**
 * Core fetch wrapper. Throws `ApiError` for non-2xx responses and network
 * failures. Never returns a non-ok Response.
 */
async function apiFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const url = `${API_BASE_URL}${path}`;

  // FormData(multipart) 본문일 때는 Content-Type 을 직접 지정하지 않는다 —
  // 브라우저가 boundary 가 포함된 `multipart/form-data; boundary=...` 헤더를
  // 자동으로 설정하기 때문. JSON 본문에만 application/json 을 기본값으로 둔다.
  const isFormData =
    typeof FormData !== "undefined" && init.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(init.headers as Record<string, string> | undefined),
  };

  let response: Response;
  try {
    response = await fetch(url, { ...init, headers });
  } catch {
    throw new ApiError(0, "서버 연결 실패. 잠시 후 다시 시도해 주세요.");
  }

  if (response.ok) return response;

  // Parse error body
  let detail = "알 수 없는 오류가 발생했습니다.";
  try {
    const body: unknown = await response.json();
    if (
      body !== null &&
      typeof body === "object" &&
      "detail" in body
    ) {
      const raw = (body as { detail: unknown }).detail;
      if (typeof raw === "string") {
        detail = raw;
      } else if (Array.isArray(raw)) {
        detail = normalisePydanticDetail(
          raw as Array<{ loc: unknown[]; msg: string; type: string }>
        );
      }
    }
  } catch {
    // ignore JSON parse failure — keep default message
  }

  throw new ApiError(response.status, detail);
}

// ── Public API functions ───────────────────────────────────────────────────

export async function signupApi(req: SignupRequest): Promise<TokenResponse> {
  const response = await apiFetch("/auth/signup", {
    method: "POST",
    body: JSON.stringify(req),
  });
  return response.json() as Promise<TokenResponse>;
}

export async function loginApi(req: LoginRequest): Promise<TokenResponse> {
  const response = await apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify(req),
  });
  return response.json() as Promise<TokenResponse>;
}

export async function refreshApi(
  refreshToken: string
): Promise<AccessTokenResponse> {
  const response = await apiFetch("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  return response.json() as Promise<AccessTokenResponse>;
}

/**
 * Authenticated fetch wrapper. Reads the stored access token from auth.ts
 * and attaches it as a Bearer token. Falls back to unauthenticated request
 * when no token is present.
 *
 * 401 자동 처리 (issue #72): 응답이 401 이면 `ensureFreshAccessToken(force=true)`
 * 로 refresh 시도 후 *같은 요청을 단 1회* 재시도. 새 토큰을 얻지 못하거나 두 번째
 * 호출도 401 이면 원본 ApiError 를 그대로 throw. 무한 루프 방지를 위해 retry 는
 * 단일.
 *
 * **`init.body` 주의**: `ReadableStream` 같은 1회용 본문은 retry 호출 시 비어있어
 * 서버가 400/422 를 반환할 수 있다. 일반 JSON 사용 (`JSON.stringify(...)` → 문자열)
 * 케이스는 안전.
 *
 * Import is deferred to avoid a circular-dependency at module evaluation time.
 */
export async function authedFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  // Dynamic import avoids a circular reference between api.ts ↔ auth.ts at
  // module load time while still keeping the dependency explicit.
  const { getAccessToken, ensureFreshAccessToken } = await import("./auth");

  const callWith = (token: string | null): Promise<Response> =>
    apiFetch(path, {
      ...init,
      headers: {
        ...(init.headers as Record<string, string> | undefined),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

  try {
    return await callWith(getAccessToken());
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 401) throw err;

    // 401 — 서버가 토큰을 거부. force=true 로 만료 검사를 건너뛰고 refresh 시도.
    let newToken: string | null;
    try {
      newToken = await ensureFreshAccessToken(true);
    } catch {
      // refresh 호출 자체가 실패 (서버측 refresh token 무효). ensureFreshAccessToken
      // 이 이미 clearTokens 처리했으므로 원본 401 을 그대로 던진다.
      throw err;
    }

    if (!newToken) throw err;

    // 단일 retry — 두 번째 호출이 또 401 을 던지면 catch 없이 그대로 전파.
    return callWith(newToken);
  }
}

/**
 * 녹음한 음성 Blob 을 `POST /recommend` 로 업로드한다 (US-3, FR2.4).
 *
 * multipart/form-data 의 `audio` 필드로 전송 (백엔드 `recommend(audio: UploadFile)`
 * 시그니처와 일치). 인증이 필요한 엔드포인트이므로 `authedFetch` 로 Bearer 토큰을
 * 자동 첨부한다. 운영 환경(`NEXT_PUBLIC_API_BASE_URL`)에서는 TLS(https) 로 전송된다
 * (NFR3.1). 비-2xx 응답·네트워크 실패는 `ApiError` 로 throw 된다.
 *
 * @param audio   녹음 결과 Blob (예: `audio/webm`)
 * @param filename 서버에 전달할 파일명 (기본 `recording.webm`)
 */
export async function recommendApi(
  audio: Blob,
  filename = "recording.webm"
): Promise<unknown> {
  const form = new FormData();
  form.append("audio", audio, filename);

  const response = await authedFetch("/recommend", {
    method: "POST",
    body: form,
  });
  // raw 응답 — 호출자가 toRecommendResult 로 도메인 타입 변환.
  return response.json() as Promise<unknown>;
}

/**
 * 곡 피드백 (좋아요/싫어요) — `POST /feedback/{like|dislike}` (#47, FR6.1).
 * 설계상 append-only(취소 없음). recommendationId 는 추천 세션 식별자
 * (`RecommendResult.sessionId`).
 */
export async function feedbackApi(
  type: FeedbackType,
  trackId: string,
  recommendationId: string
): Promise<void> {
  await authedFetch(`/feedback/${type}`, {
    method: "POST",
    body: JSON.stringify({
      track_id: trackId,
      recommendation_id: recommendationId,
    }),
  });
}

/**
 * 재생 이벤트 로깅 — `POST /feedback/playback` (#48, FR6.2).
 * @param event start | end | complete
 * @param playbackPct 재생 진행률(0~100). 생략 가능.
 */
export async function playbackApi(
  trackId: string,
  event: PlaybackEvent,
  playbackPct?: number
): Promise<void> {
  await authedFetch("/feedback/playback", {
    method: "POST",
    body: JSON.stringify({
      track_id: trackId,
      event,
      ...(playbackPct !== undefined ? { playback_pct: playbackPct } : {}),
    }),
  });
}

/**
 * 서버측 refresh token revoke — `POST /auth/logout` (FR1.x).
 * 204 No Content 응답이므로 JSON 파싱 없음.
 * @param refreshToken 현재 보관 중인 refresh token
 */
export async function logoutApi(refreshToken: string): Promise<void> {
  await authedFetch("/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

/**
 * 추천 이력 조회 — `GET /history?n=` (#50, FR6.5).
 * @param n 최근 N개 (생략 시 백엔드 기본값).
 */
export async function historyApi(n?: number): Promise<HistoryItem[]> {
  const query = n !== undefined ? `?n=${n}` : "";
  const response = await authedFetch(`/history${query}`, { method: "GET" });
  return response.json() as Promise<HistoryItem[]>;
}
