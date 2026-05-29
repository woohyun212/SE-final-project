/**
 * recommend.tsx — US-5 추천 곡 리스트 페이지 (#20)
 *
 * 추천 응답을 받아 RecommendationVisualizer 로 렌더. 실제 오디오 녹음은
 * US-3(#18) 작업 — 본 페이지는 임시 트리거 버튼으로 backend `/recommend`
 * 라운드트립을 검증한다. #18 머지 후 녹음된 Blob 을 그대로 넘기도록 교체.
 */

import Head from 'next/head';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import RecommendationVisualizer, {
  type Track as VisualizerTrack,
} from '../components/RecommendationVisualizer';
import EmotionMusicChart from '../components/EmotionMusicChart';
import { RecommendationReasonList } from '../components/RecommendationReasonCard';
import { recommendApi, ApiError } from '../lib/api';
import {
  MOCK_RECOMMEND_RESULT,
  loadRecommendResult,
  clearRecommendResult,
} from '../lib/recommend';
import { useAuthGuard } from '../lib/useAuthGuard';

const FONT_URL =
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap';

/** 임시 트리거용 더미 오디오 Blob. 백엔드는 audio 내용을 무시하고 더미 트랙을
 *  반환한다 (#18 머지 전까지의 placeholder). */
function createPlaceholderAudio(): Blob {
  return new Blob([new Uint8Array(16)], { type: 'audio/wav' });
}

export default function RecommendPage() {
  useAuthGuard();

  const [tracks, setTracks] = useState<VisualizerTrack[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromVoice, setFromVoice] = useState(false);

  // 녹음 화면(/)에서 넘어온 추천 결과가 있으면 마운트 시 로드해 리스트 렌더.
  // 1회성 핸드오프 — 로드 직후 클리어해, 재녹음 없이 /recommend 재진입 시
  // 옛 결과가 다시 뜨지 않도록 한다. 직접 진입(저장값 없음)이면 수동 버튼 동선 유지.
  useEffect(() => {
    const stored = loadRecommendResult();
    if (stored && stored.tracks.length > 0) {
      setTracks(stored.tracks);
      setFromVoice(true);
      clearRecommendResult();
    }
  }, []);

  const handleFetch = useCallback(async () => {
    setFromVoice(false); // 수동 재요청 — 출처를 '음성'에서 전환
    setLoading(true);
    setError(null);
    try {
      const response = await recommendApi(createPlaceholderAudio());
      setTracks(response.tracks);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(
          err.status === 401
            ? '로그인이 만료되었습니다. 다시 로그인해 주세요.'
            : `오류가 발생했습니다. (${err.status}) ${err.detail}`,
        );
      } else if (err instanceof TypeError) {
        setError('서버 연결 실패. 잠시 후 다시 시도해 주세요.');
      } else {
        setError('알 수 없는 오류가 발생했습니다.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <>
      <Head>
        <title>추천 곡 — SE Final Project</title>
        <meta name="description" content="AI 감정 분석 기반 추천 곡 리스트" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href={FONT_URL} rel="stylesheet" />
        <style>{`body { font-family: 'Noto Sans KR', system-ui, sans-serif; margin: 0; }`}</style>
      </Head>

      <main
        style={{
          maxWidth: 640,
          margin: '0 auto',
          padding: '48px 24px 96px',
        }}
      >
        <header style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: '1.75rem', margin: 0, color: '#0f172a' }}>추천 곡</h1>
          <p style={{ margin: '8px 0 0', color: '#6b7280', fontSize: '0.95rem' }}>
            {fromVoice
              ? '방금 녹음한 음성의 감정 분석 결과로 추천된 곡이에요.'
              : '감정 분석 기반 추천 트랙 리스트'}
          </p>
        </header>

        <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
          <button
            type="button"
            onClick={handleFetch}
            disabled={loading}
            aria-busy={loading}
            style={{
              padding: '10px 18px',
              borderRadius: 8,
              border: 0,
              background: loading ? '#93c5fd' : '#1976D2',
              color: '#fff',
              fontWeight: 600,
              fontSize: '0.95rem',
              cursor: loading ? 'progress' : 'pointer',
            }}
          >
            {loading ? '불러오는 중…' : fromVoice ? '다시 추천 받기' : '추천 받기'}
          </button>
          <Link
            href="/"
            style={{
              padding: '10px 18px',
              borderRadius: 8,
              background: '#f0f4f8',
              color: '#1976D2',
              fontWeight: 500,
              fontSize: '0.95rem',
              textDecoration: 'none',
              display: 'inline-flex',
              alignItems: 'center',
            }}
          >
            홈
          </Link>
        </div>

        <RecommendationVisualizer
          tracks={tracks}
          loading={loading}
          error={error}
        />

        <section style={{ marginTop: 40 }}>
          <h2 style={{ fontSize: '1.25rem', margin: '0 0 12px', color: '#0f172a' }}>
            감정-음악 매핑
          </h2>
          <p style={{ margin: '0 0 16px', color: '#6b7280', fontSize: '0.9rem' }}>
            내 감정과 추천 곡의 valence×energy 관계 (preview: mock 데이터)
          </p>
          <EmotionMusicChart
            tracks={MOCK_RECOMMEND_RESULT.tracks}
            userEmotion={MOCK_RECOMMEND_RESULT.userEmotion}
          />
        </section>

        <section style={{ marginTop: 40 }}>
          <h2 style={{ fontSize: '1.25rem', margin: '0 0 12px', color: '#0f172a' }}>
            추천 이유
          </h2>
          <p style={{ margin: '0 0 16px', color: '#6b7280', fontSize: '0.9rem' }}>
            각 곡을 추천한 이유 (preview: mock 데이터)
          </p>
          <RecommendationReasonList tracks={MOCK_RECOMMEND_RESULT.tracks} />
        </section>
      </main>
    </>
  );
}
