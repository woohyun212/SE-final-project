/**
 * useAuthGuard / useGuestGuard 단위 테스트.
 * - 미인증 시 /login 리다이렉트
 * - 인증 시 통과 (리다이렉트 없음)
 * - 토큰 refresh 실패(throw) 시 /login 리다이렉트
 * - router.isReady = false 일 때 아무것도 하지 않음
 * - useGuestGuard: 이미 로그인된 경우 / 로 리다이렉트
 * - useGuestGuard: 미인증 시 통과
 * - redirectTo 커스텀 경로 지원
 */
import { renderHook, act } from "@testing-library/react";
import { useAuthGuard, useGuestGuard } from "../lib/useAuthGuard";
import { ensureFreshAccessToken, isAuthenticated } from "../lib/auth";

// ── Mocks ──────────────────────────────────────────────────────────────────

const mockPush = jest.fn();

jest.mock("next/router", () => ({
  useRouter: jest.fn(),
}));

jest.mock("../lib/auth", () => ({
  ensureFreshAccessToken: jest.fn(),
  isAuthenticated: jest.fn(),
}));

const mockEnsureFresh = ensureFreshAccessToken as jest.MockedFunction<
  typeof ensureFreshAccessToken
>;
const mockIsAuthenticated = isAuthenticated as jest.MockedFunction<
  typeof isAuthenticated
>;

// Import after mocking so useRouter is mocked
import { useRouter } from "next/router";
const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;

// ── Helpers ────────────────────────────────────────────────────────────────

function makeRouter(isReady: boolean) {
  return {
    isReady,
    push: mockPush,
    pathname: "/",
    query: {},
    asPath: "/",
    route: "/",
    events: { on: jest.fn(), off: jest.fn(), emit: jest.fn() },
    replace: jest.fn(),
    back: jest.fn(),
    prefetch: jest.fn(),
    reload: jest.fn(),
    beforePopState: jest.fn(),
  } as unknown as ReturnType<typeof useRouter>;
}

/** Flush all pending microtasks / state updates. */
async function flushAsync() {
  await act(async () => {
    await Promise.resolve();
  });
}

// ── Setup / Teardown ───────────────────────────────────────────────────────

beforeEach(() => {
  mockPush.mockResolvedValue(true);
});

afterEach(() => {
  jest.clearAllMocks();
});

// ── useAuthGuard tests ─────────────────────────────────────────────────────

describe("useAuthGuard", () => {
  it("router.isReady=false 일 때 아무것도 하지 않음", async () => {
    mockUseRouter.mockReturnValue(makeRouter(false));
    mockEnsureFresh.mockResolvedValue("token");

    renderHook(() => useAuthGuard());
    await flushAsync();

    expect(mockEnsureFresh).not.toHaveBeenCalled();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("유효한 토큰 반환 시 리다이렉트 없음 (인증 통과)", async () => {
    mockUseRouter.mockReturnValue(makeRouter(true));
    mockEnsureFresh.mockResolvedValue("valid-access-token");

    renderHook(() => useAuthGuard());
    await flushAsync();

    expect(mockEnsureFresh).toHaveBeenCalledTimes(1);
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("ensureFreshAccessToken이 null 반환 시 /login 으로 리다이렉트", async () => {
    mockUseRouter.mockReturnValue(makeRouter(true));
    mockEnsureFresh.mockResolvedValue(null);

    renderHook(() => useAuthGuard());
    await flushAsync();

    expect(mockPush).toHaveBeenCalledWith("/login");
  });

  it("ensureFreshAccessToken이 throw 시 /login 으로 리다이렉트", async () => {
    mockUseRouter.mockReturnValue(makeRouter(true));
    mockEnsureFresh.mockRejectedValue(new Error("refresh failed"));

    renderHook(() => useAuthGuard());
    await flushAsync();

    expect(mockPush).toHaveBeenCalledWith("/login");
  });

  it("커스텀 redirectTo 경로로 리다이렉트", async () => {
    mockUseRouter.mockReturnValue(makeRouter(true));
    mockEnsureFresh.mockResolvedValue(null);

    renderHook(() => useAuthGuard("/custom-login"));
    await flushAsync();

    expect(mockPush).toHaveBeenCalledWith("/custom-login");
  });

  it("언마운트 후 push 호출 안 함 (cancelled 플래그)", async () => {
    mockUseRouter.mockReturnValue(makeRouter(true));

    // ensureFreshAccessToken이 언마운트 후에 resolve
    let resolveToken!: (v: string | null) => void;
    mockEnsureFresh.mockReturnValue(
      new Promise<string | null>((res) => {
        resolveToken = res;
      })
    );

    const { unmount } = renderHook(() => useAuthGuard());

    // 아직 resolve 전에 언마운트
    unmount();

    // 이후 null 로 resolve
    await act(async () => {
      resolveToken(null);
      await Promise.resolve();
    });

    expect(mockPush).not.toHaveBeenCalled();
  });
});

// ── useGuestGuard tests ────────────────────────────────────────────────────

describe("useGuestGuard", () => {
  it("router.isReady=false 일 때 아무것도 하지 않음", async () => {
    mockUseRouter.mockReturnValue(makeRouter(false));
    mockIsAuthenticated.mockReturnValue(true);

    renderHook(() => useGuestGuard());
    await flushAsync();

    expect(mockPush).not.toHaveBeenCalled();
  });

  it("이미 로그인된 상태면 / 로 리다이렉트", async () => {
    mockUseRouter.mockReturnValue(makeRouter(true));
    mockIsAuthenticated.mockReturnValue(true);

    renderHook(() => useGuestGuard());
    await flushAsync();

    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("미인증 상태면 리다이렉트 없음 (게스트 통과)", async () => {
    mockUseRouter.mockReturnValue(makeRouter(true));
    mockIsAuthenticated.mockReturnValue(false);

    renderHook(() => useGuestGuard());
    await flushAsync();

    expect(mockPush).not.toHaveBeenCalled();
  });

  it("커스텀 redirectTo 경로로 리다이렉트", async () => {
    mockUseRouter.mockReturnValue(makeRouter(true));
    mockIsAuthenticated.mockReturnValue(true);

    renderHook(() => useGuestGuard("/dashboard"));
    await flushAsync();

    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });
});
