/**
 * recommend.tsx — 추천 결과 화면 (#20 리스트 + #45 차트 + #46 이유).
 *
 * 녹음 화면(/)에서 sessionStorage 로 넘어온 추천 결과(RecommendResult)를 로드해
 * 리스트·2D 감정차트·추천 이유를 모두 실데이터로 렌더한다.
 *
 * 직접 진입(저장값 없음) 시에는 빈 상태 안내 + "녹음하러 가기" CTA 만 표시한다.
 * RecommendationVisualizer 의 빈 상태와 중복되지 않도록, 결과가 없으면
 * Visualizer 자체를 렌더하지 않는다.
 *
 * 백엔드 /recommend 응답(snake_case·중첩)은 toRecommendResult 어댑터(#114)가
 * 도메인 RecommendResult 로 변환한다.
 */

import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import RecommendationVisualizer from '../components/RecommendationVisualizer';
import EmotionMusicChart from '../components/EmotionMusicChart';
import { RecommendationReasonList } from '../components/RecommendationReasonCard';
import FeedbackButtons from '../components/FeedbackButtons';
import AudioPlayer from '../components/AudioPlayer';
import {
  type RecommendResult,
  type FeedbackType,
  loadRecommendResult,
  clearRecommendResult,
} from '../lib/recommend';
import { useAuthGuard } from '../lib/useAuthGuard';
import { usePlaybackLogger } from '../lib/usePlaybackLogger';
import { useTrackEnrichment } from '../lib/useTrackEnrichment';

const FONT_URL =
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap';

// ── 한국어 매핑 테이블 ─────────────────────────────────────────────────────────

/** time_of_day → 한국어 */
const TIME_OF_DAY_KO: Record<string, string> = {
  morning: '아침',
  afternoon: '오후',
  evening: '저녁',
  night: '밤',
};

/** location → 한국어 */
const LOCATION_KO: Record<string, string> = {
  home: '집',
  commute: '이동 중',
  gym: '헬스장',
  office: '사무실',
  outdoor: '야외',
  cafe: '카페',
};

/** activity → 한국어 */
const ACTIVITY_KO: Record<string, string> = {
  working: '일하는 중',
  exercising: '운동 중',
  relaxing: '쉬는 중',
  studying: '공부 중',
  commuting: '출퇴근 중',
  socializing: '사람들과 함께',
};

/** 감정 영문 키 → 한국어 레이블 — backend `_EMOTION_LABELS` 7종과 1:1 (schemas/context.py). */
const EMOTION_KO: Record<string, string> = {
  happy: '행복',
  sad: '슬픔',
  angry: '화남',
  anxious: '불안',
  calm: '차분',
  energetic: '활기',
  melancholic: '우울',
};

// ── 상황 칩 컴포넌트 ──────────────────────────────────────────────────────────

interface ChipProps {
  label: string;
}

/** 컨텍스트 라벨 칩 — 인라인 스타일(기존 페이지 패턴 유지). */
function Chip({ label }: ChipProps) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '4px 10px',
        borderRadius: 20,
        fontSize: '0.8125rem',
        fontWeight: 500,
        background: '#dbeafe',
        color: '#1e40af',
        letterSpacing: '-0.01em',
        lineHeight: 1.4,
      }}
    >
      {label}
    </span>
  );
}

/** 다크모드용 chip 배경 · 텍스트는 CSS media query 를 인라인에서 적용할 수 없으므로
 *  recommend.module.css 의 CSS 변수에 의존하지 않고 별도 className 을 쓰지 않는다.
 *  대신 Chip 과 EmotionChip 은 동일 팔레트(파란 계열)를 유지한다.
 */

interface EmotionChipProps {
  label: string;
  pct: number;
}

/** 감정 확률 칩 — "행복 42%" 형식. */
function EmotionChip({ label, pct }: EmotionChipProps) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '4px 10px',
        borderRadius: 20,
        fontSize: '0.8125rem',
        fontWeight: 500,
        background: '#ede9fe',
        color: '#4c1d95',
        letterSpacing: '-0.01em',
        lineHeight: 1.4,
      }}
    >
      {label} {pct}%
    </span>
  );
}

// ── 직접 진입 빈 상태 ─────────────────────────────────────────────────────────

/** 저장된 결과 없이 직접 진입했을 때 표시하는 안내 + CTA. */
function NoResultGuide() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 16,
        padding: '64px 24px',
        textAlign: 'center',
      }}
    >
      {/* 마이크 아이콘 */}
      <span aria-hidden="true" style={{ color: '#c7d8ee' }}>
        <svg width="56" height="56" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3Zm-1 3a1 1 0 0 1 2 0v8a1 1 0 0 1-2 0V4Zm-5 8a6 6 0 0 0 12 0h-2a4 4 0 0 1-8 0H6Zm6 6a7.003 7.003 0 0 1-6.929-6H3.07A9.004 9.004 0 0 0 11 19.945V22h2v-2.055A9.004 9.004 0 0 0 20.929 12H18.93A7.003 7.003 0 0 1 12 18Z" />
        </svg>
      </span>
      <p
        style={{
          fontSize: '0.9375rem',
          fontWeight: 600,
          color: '#6b7280',
          margin: 0,
          letterSpacing: '-0.01em',
        }}
      >
        아직 추천 결과가 없어요.
      </p>
      <p
        style={{
          fontSize: '0.8125rem',
          color: '#6b7280',
          margin: 0,
          opacity: 0.7,
        }}
      >
        녹음 화면에서 음성을 녹음하면 감정 분석 후 곡을 추천해 드려요.
      </p>
      <Link
        href="/"
        style={{
          marginTop: 8,
          padding: '11px 24px',
          borderRadius: 10,
          background: '#1976D2',
          color: '#fff',
          fontWeight: 600,
          fontSize: '0.9375rem',
          textDecoration: 'none',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          letterSpacing: '-0.01em',
        }}
      >
        {/* 마이크 아이콘(소) */}
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3Zm-1 3a1 1 0 0 1 2 0v8a1 1 0 0 1-2 0V4Zm-5 8a6 6 0 0 0 12 0h-2a4 4 0 0 1-8 0H6Zm6 6a7.003 7.003 0 0 1-6.929-6H3.07A9.004 9.004 0 0 0 11 19.945V22h2v-2.055A9.004 9.004 0 0 0 20.929 12H18.93A7.003 7.003 0 0 1 12 18Z" />
        </svg>
        녹음하러 가기
      </Link>
    </div>
  );
}

// ── 메인 페이지 ───────────────────────────────────────────────────────────────

export default function RecommendPage() {
  useAuthGuard();

  const [result, setResult] = useState<RecommendResult | null>(null);
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
      clearRecommendResult();
    }
  }, []);

  const tracks = result?.tracks ?? [];
  const hasResult = tracks.length > 0;

  // preview_url 이 null 인 곡만 iTunes 로 미리듣기·앨범아트 보강 (FR5.4 / FR5.2 / FR6.2).
  // 백엔드가 채운 preview_url 은 우선되고, 보강은 마운트 후 lazy 진행.
  const enrichments = useTrackEnrichment(tracks);

  // 곡별 병합값 헬퍼 — 보강 결과를 백엔드 값보다 후순위로 합친다.
  const mergedPreviewUrl = (t: (typeof tracks)[number]): string | null =>
    t.preview_url ?? enrichments[t.track_id ?? '']?.previewUrl ?? null;
  const mergedArtworkUrl = (t: (typeof tracks)[number]): string | null =>
    enrichments[t.track_id ?? '']?.artworkUrl ?? null;

  // ── context 칩 목록 계산 ────────────────────────────────────────────────────
  const contextChips: string[] = [];
  if (result?.context) {
    const { time_of_day, location, activity } = result.context;
    if (time_of_day) contextChips.push(TIME_OF_DAY_KO[time_of_day] ?? time_of_day);
    if (location) contextChips.push(LOCATION_KO[location] ?? location);
    if (activity) contextChips.push(ACTIVITY_KO[activity] ?? activity);
  }

  // ── context emotions 칩 목록 ────────────────────────────────────────────────
  const emotionChips: Array<{ label: string; pct: number }> = [];
  if (result?.context?.emotions) {
    for (const [key, val] of Object.entries(result.context.emotions)) {
      emotionChips.push({
        label: EMOTION_KO[key] ?? key,
        pct: Math.round(val * 100),
      });
    }
  }

  // ── fallback 이유 경고 여부 ─────────────────────────────────────────────────
  const showFallbackReasonNote = result?.fallbackFlags?.reason === true;

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
        {/* ── 헤더 ── */}
        <header style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: '1.75rem', margin: 0, color: '#0f172a' }}>추천 곡</h1>
          <p style={{ margin: '8px 0 0', color: '#6b7280', fontSize: '0.95rem' }}>
            {hasResult
              ? '방금 녹음한 음성의 감정 분석 결과로 추천된 곡이에요.'
              : '감정 분석 기반 추천 트랙 리스트'}
          </p>
        </header>

        {/* ── 네비게이션 링크 ── */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
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

        {/* ── 직접 진입(결과 없음) → 안내만 표시, Visualizer 렌더 안 함 ── */}
        {!hasResult ? (
          <NoResultGuide />
        ) : (
          <>
            {/* ── transcript 인용 블록 ── */}
            {result?.transcript && (
              <blockquote
                style={{
                  margin: '0 0 28px',
                  padding: '14px 18px',
                  borderLeft: '3px solid #1976D2',
                  background: '#f0f7ff',
                  borderRadius: '0 10px 10px 0',
                  color: '#374151',
                  fontSize: '0.9rem',
                  lineHeight: 1.6,
                  fontStyle: 'italic',
                }}
              >
                <span
                  style={{
                    display: 'block',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    fontStyle: 'normal',
                    color: '#1976D2',
                    marginBottom: 6,
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                  }}
                >
                  내 이야기
                </span>
                {result.transcript}
              </blockquote>
            )}

            {/* ── context 칩 섹션 ── */}
            {(contextChips.length > 0 || emotionChips.length > 0) && (
              <div style={{ marginBottom: 28 }}>
                {contextChips.length > 0 && (
                  <div
                    style={{
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: 6,
                      marginBottom: emotionChips.length > 0 ? 8 : 0,
                    }}
                    aria-label="녹음 시점 상황"
                  >
                    {contextChips.map((label) => (
                      <Chip key={label} label={label} />
                    ))}
                  </div>
                )}
                {emotionChips.length > 0 && (
                  <div
                    style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}
                    aria-label="감지된 감정"
                  >
                    {emotionChips.map(({ label, pct }) => (
                      <EmotionChip key={label} label={label} pct={pct} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── 추천 곡 리스트 ── */}
            <RecommendationVisualizer
              tracks={tracks.map((t) => ({
                ...t,
                // 백엔드 preview_url 우선, 없으면 iTunes 보강값 (FR5.4).
                preview_url: mergedPreviewUrl(t),
                // 앨범아트는 보강값 — 없으면 Visualizer 가 placeholder fallback (FR5.2).
                artwork_url: mergedArtworkUrl(t),
              }))}
              loading={false}
              error={null}
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

            {/* ── 감정-음악 매핑 차트 ── */}
            <section style={{ marginTop: 40 }}>
              <h2 style={{ fontSize: '1.25rem', margin: '0 0 12px', color: '#0f172a' }}>
                감정-음악 매핑
              </h2>
              <p style={{ margin: '0 0 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                내 감정과 추천 곡의 valence×energy 관계
              </p>
              <EmotionMusicChart tracks={result!.tracks} userEmotion={result!.userEmotion} />
            </section>

            {/* ── 추천 이유 섹션 ── */}
            <section style={{ marginTop: 40 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 12 }}>
                <h2 style={{ fontSize: '1.25rem', margin: 0, color: '#0f172a' }}>
                  추천 이유
                </h2>
                {/* fallback reason 안내 — fallbackFlags.reason === true 일 때만 표시 */}
                {showFallbackReasonNote && (
                  <span
                    style={{
                      fontSize: '0.75rem',
                      color: '#9ca3af',
                      fontStyle: 'italic',
                    }}
                    aria-label="추천 이유 생성 방식 안내"
                  >
                    (이유는 기본 규칙으로 생성됨)
                  </span>
                )}
              </div>
              <p style={{ margin: '0 0 16px', color: '#6b7280', fontSize: '0.9rem' }}>
                각 곡을 추천한 이유
              </p>
              <RecommendationReasonList tracks={result!.tracks} />
            </section>
          </>
        )}
      </main>
    </>
  );
}
