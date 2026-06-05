/**
 * history.tsx — 추천 이력 조회 화면 (#50, US-20).
 *
 * 마운트 시 historyApi() 로 GET /history 를 호출해 HistoryItem[] 을 받아
 * HistoryList 컴포넌트로 렌더한다. 로그인이 필요한 페이지이므로
 * useAuthGuard() 로 미인증 시 /login 으로 리다이렉트한다.
 *
 * ApiError / 네트워크 오류는 상태로 보관해 HistoryList 의 에러 슬롯으로 전달한다.
 */

import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import HistoryList from '../components/HistoryList';
import { historyApi, ApiError } from '../lib/api';
import type { HistoryItem } from '../lib/recommend';
import { useAuthGuard } from '../lib/useAuthGuard';
import styles from '../styles/history.module.css';

const FONT_URL =
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap';

export default function HistoryPage() {
  useAuthGuard();

  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await historyApi();
        if (!cancelled) {
          setItems(data);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        if (err instanceof ApiError) {
          setError(
            err.status === 401
              ? '로그인이 만료되었습니다. 다시 로그인해 주세요.'
              : `이력을 불러올 수 없습니다. (${err.status}) ${err.detail}`,
          );
        } else {
          setError('서버 연결 실패. 잠시 후 다시 시도해 주세요.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <Head>
        <title>추천 이력 — SE Final Project</title>
        <meta name="description" content="AI 감정 분석 기반 추천 이력 조회" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href={FONT_URL} rel="stylesheet" />
        <style>{`body { font-family: 'Noto Sans KR', system-ui, sans-serif; margin: 0; }`}</style>
      </Head>

      <div className={styles.page}>
        <main className={styles.inner}>
          {/* ── Page header ── */}
          <header className={styles.header}>
            <div className={styles.headerTop}>
              <h1 className={styles.title}>추천 이력</h1>
              <Link
                href="/"
                className={styles.backLink}
                aria-label="홈으로 돌아가기"
              >
                {/* left arrow icon */}
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 16 16"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M10 12L6 8l4-4"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                홈
              </Link>
            </div>
            <p className={styles.subtitle}>
              최근 추천 세션 이력과 피드백한 곡을 확인할 수 있습니다.
            </p>
          </header>

          {/* ── History list ── */}
          <HistoryList items={items} loading={loading} error={error} />
        </main>
      </div>
    </>
  );
}
