const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
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
 * Import is deferred to avoid a circular-dependency at module evaluation time.
 */
export async function authedFetch(
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  // Dynamic import avoids a circular reference between api.ts ↔ auth.ts at
  // module load time while still keeping the dependency explicit.
  const { getAccessToken } = await import("./auth");
  const token = getAccessToken();

  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  return apiFetch(path, {
    ...init,
    headers: {
      ...(init.headers as Record<string, string> | undefined),
      ...authHeaders,
    },
  });
}
