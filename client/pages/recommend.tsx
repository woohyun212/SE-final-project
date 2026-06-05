/**
 * recommend.tsx — 추천 결과 화면 (#20 리스트 + #45 차트 + #46 이유).
 *
 * 녹음 화면(/)에서 sessionStorage 로 넘어온 추천 결과(RecommendResult)를 로드해
 * 리스트·2D 감정차트·추천 이유를 모두 실데이터로 렌더한다. 직접 진입(저장값 없음)
 * 시에는 수동 "추천 받기" 버튼으로 placeholder 오디오를 보내 라운드트립을 확인한다.
 *
 * 백엔드 /recommend 응답(snake_case·중첩)은 toRecommendResult 어댑터(#114)가
 * 도메인 RecommendResult 로 변환한다.
 */

import Head from 'next/head';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import RecommendationVisualizer from '../components/RecommendationVisualizer';
import EmotionMusicChart from '../components/EmotionMusicChart';
import { RecommendationReasonList } from '../components/RecommendationReasonCard';
import FeedbackButtons from '../components/FeedbackButtons';
import AudioPlayer from '../components/AudioPlayer';
import { recommendApi, ApiError } from '../lib/api';
import {
  type RecommendResult,
  type FeedbackType,
  toRecommendResult,
  loadRecommendResult,
  clearRecommendResult,
} from '../lib/recommend';
import { useAuthGuard } from '../lib/useAuthGuard';
import { usePlaybackLogger } from '../lib/usePlaybackLogger';

const FONT_URL =
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap';

/** 직접 진입 시 수동 트리거용 더미 오디오 Blob (placeholder). */
function createPlaceholderAudio(): Blob {
  return new Blob([new Uint8Array(16)], { type: 'audio/wav' });
}

export default function RecommendPage() {
  useAuthGuard();

  const [result, setResult] = useState<RecommendResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromVoice, setFromVoice] = useState(false);
  /** 곡별 피드백 상태 — key: track_id, value: 'like' | 'dislike' (#47). */
  const [feedback, setFeedback] = useState<Record<string, FeedbackType>>({});
  /** 미리듣기 재생 + start/end/complete 이벤트 로깅 (#48). */
  const { playingId, toggle } = usePlaybackLogger();

  // 녹음 화면(/)에서 넘어온 추천 결과가 있으면 마운트 시 로드.
  // 1회성 핸드오프 — 로드 직후 클리어해, 재녹음 없이 /recommend 재진입 시
  // 옛 결과가 다시 뜨지 않도록 한다.
  useEffect(() => {
    const stored = loadRecommendResult();
    if (stored && stored.tracks.length > 0) {
      setResult(stored);
      setFromVoice(true);
      clearRecommendResult();
    }
  }, []);

  const handleFetch = useCallback(async () => {
    setFromVoice(false); // 수동 재요청 — 출처를 '음성'에서 전환
    setLoading(true);
    setError(null);
    try {
      const raw = await recommendApi(createPlaceholderAudio());
      setResult(toRecommendResult(raw));
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

  const tracks = result?.tracks ?? [];
  const hasResult = tracks.length > 0;

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
          <Link
            href="/history"
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
            추천 이력
          </Link>
        </div>

        <RecommendationVisualizer
          tracks={tracks}
          loading={loading}
          error={error}
          renderRowActions={(t) => (
            <>
              <AudioPlayer
                previewUrl={t.preview_url}
                playing={playingId === t.track_id}
                onToggle={() =>
                  toggle({
                    trackId: t.track_id ?? '',
                    previewUrl: t.preview_url ?? null,
                  })
                }
              />
              <FeedbackButtons
                trackId={t.track_id ?? ''}
                recommendationId={result?.sessionId}
                value={feedback[t.track_id ?? ''] ?? null}
                onChange={(v) =>
                  setFeedback((prev) => ({ ...prev, [t.track_id ?? '']: v }))
                }
              />
            </>
          )}
        />

        {hasResult && result && (
          <>
            <section style={{ marginTop: 40 }}>
              <h2 style={{ fontSize: '1.25rem', margin: '0 0 12px', color: '#0f172a' }}>
                감정-음악 매핑
              </h2>
              <p style={{ margin: '0 0 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                내 감정과 추천 곡의 valence×energy 관계
              </p>
              <EmotionMusicChart tracks={result.tracks} userEmotion={result.userEmotion} />
            </section>

            <section style={{ marginTop: 40 }}>
              <h2 style={{ fontSize: '1.25rem', margin: '0 0 12px', color: '#0f172a' }}>
                추천 이유
              </h2>
              <p style={{ margin: '0 0 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                각 곡을 추천한 이유
              </p>
              <RecommendationReasonList tracks={result.tracks} />
            </section>
          </>
        )}
      </main>
    </>
  );
}
