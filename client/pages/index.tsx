/**
 * index.tsx — 메인 화면 (로그인 필요).
 *
 * US-3 (이슈 #18): 메인 화면에서 음성을 녹음(VoiceCapture)하고 백엔드로 전송한다.
 * useAuthGuard 로 비인증 사용자는 /login 으로 보낸다.
 */
import Head from 'next/head';
import { useRouter } from 'next/router';
import { useCallback } from 'react';

import VoiceCapture from '../components/VoiceCapture';
import { logout, getRefreshToken } from '../lib/auth';
import { logoutApi } from '../lib/api';
import { saveRecommendResult, type RecommendResult } from '../lib/recommend';
import { useAuthGuard } from '../lib/useAuthGuard';

import styles from '../styles/home.module.css';

const FONT_URL =
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap';

export default function Home() {
  const router = useRouter();

  // 로그인 필요 — 미인증/토큰 만료 시 /login 으로 리다이렉트.
  useAuthGuard();

  const handleLogout = useCallback(async () => {
    // 서버측 revoke 를 먼저 완료시킨 뒤 토큰을 지운다. authedFetch 는 내부에서
    // 동적 import 후 access token 을 비동기로 읽으므로(api.ts), await 없이 클리어하면
    // Authorization 헤더가 빠져 /auth/logout 이 항상 401 이 된다 (PR #168 리뷰).
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await logoutApi(refreshToken);
      } catch {
        // 서버 revoke 실패해도 로컬 로그아웃 진행.
      }
    }
    logout();
    void router.push('/login');
  }, [router]);

  // 녹음 → 추천 성공 시 결과를 저장하고 추천 화면으로 이동.
  const handleResult = useCallback(
    (result: RecommendResult) => {
      saveRecommendResult(result);
      void router.push('/recommend');
    },
    [router],
  );

  return (
    <>
      <Head>
        <title>음악 추천 — AI 감정 분석 음악 추천 시스템</title>
        <meta name="description" content="음성으로 감정을 분석해 음악을 추천받으세요" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href={FONT_URL} rel="stylesheet" />
        <style>{`body { font-family: 'Noto Sans KR', system-ui, sans-serif; }`}</style>
      </Head>

      <div className={styles.page}>
        <header className={styles.topbar}>
          <span className={styles.brand}>🎵 감정 음악 추천</span>
          <button type="button" className={styles.logout} onClick={handleLogout}>
            로그아웃
          </button>
        </header>

        <main className={styles.main}>
          <div className={styles.heading}>
            <h1 className={styles.title}>지금 기분을 들려주세요</h1>
            <p className={styles.subtitle}>
              짧게 말하면 AI가 감정을 분석해 어울리는 음악을 찾아드려요.
            </p>
          </div>

          <VoiceCapture onResult={handleResult} />
        </main>
      </div>
    </>
  );
}
