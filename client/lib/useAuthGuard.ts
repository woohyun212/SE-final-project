import { useEffect } from "react";
import { useRouter } from "next/router";
import { isAuthenticated, ensureFreshAccessToken } from "./auth";

/**
 * 로그인이 *필요한* 페이지에서 호출.
 * 미인증 또는 토큰 refresh 실패 시 /login 으로 리다이렉트.
 * @param redirectTo 기본 '/login'
 */
export function useAuthGuard(redirectTo = "/login"): void {
  const router = useRouter();

  useEffect(() => {
    if (!router.isReady) return;

    let cancelled = false;

    async function check() {
      try {
        const token = await ensureFreshAccessToken();
        if (!cancelled && token === null) {
          void router.push(redirectTo);
        }
      } catch {
        if (!cancelled) {
          void router.push(redirectTo);
        }
      }
    }

    void check();

    return () => {
      cancelled = true;
    };
  }, [router.isReady, redirectTo]); // eslint-disable-line react-hooks/exhaustive-deps
}

/**
 * *비인증 사용자만* 접근 가능한 페이지(/login, /signup)에서 호출.
 * 이미 로그인된 상태면 / 로 리다이렉트.
 * @param redirectTo 기본 '/'
 */
export function useGuestGuard(redirectTo = "/"): void {
  const router = useRouter();

  useEffect(() => {
    if (!router.isReady) return;

    let cancelled = false;

    if (isAuthenticated() && !cancelled) {
      void router.push(redirectTo);
    }

    return () => {
      cancelled = true;
    };
  }, [router.isReady, redirectTo]); // eslint-disable-line react-hooks/exhaustive-deps
}
