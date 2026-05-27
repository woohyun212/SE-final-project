/**
 * RecommendationReasonCard.tsx — 추천 이유 카드 컴포넌트 (#46)
 *
 * 단일 카드: 곡 행(앨범아트 placeholder + 제목/아티스트/앨범 + 재생시간 배지) +
 * LLM 추천 이유 인용형 콜아웃(좌측 accent 바 + 틴트 배경).
 *
 * - reason null/undefined → skeleton 또는 "추천 이유 생성 중…" placeholder
 * - CSS Modules, 외부 의존성 없음, 다크모드 지원
 * - a11y: blockquote, aria-label, aria-hidden decorative SVG
 */

import type { RecommendedTrack } from '../lib/recommend';
import styles from '../styles/reasonCard.module.css';

/* ── Public types ── */

export interface RecommendationReasonCardProps {
  track: RecommendedTrack;
}

/* ── Helpers ── */

/** Format seconds as m:ss — e.g. 213 → "3:33", 247 → "4:07" */
function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

/* ── Sub-components ── */

/** 64×64 rounded album art placeholder with inline music-note SVG */
function ArtPlaceholder() {
  return (
    <div className={styles.artPlaceholder} aria-hidden="true">
      <svg
        width="28"
        height="28"
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden="true"
        focusable="false"
      >
        <path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6Z" />
      </svg>
    </div>
  );
}

/** Shimmer skeleton for missing reason — 2 lines */
function ReasonSkeleton() {
  return (
    <div
      className={styles.reasonSkeleton}
      aria-label="추천 이유 생성 중…"
      aria-busy="true"
    >
      <div className={styles.skeletonLine} />
      <div className={styles.skeletonLine} />
    </div>
  );
}

/** Reason callout (blockquote) — shown when reason is present */
function ReasonCallout({ reason }: { reason: string }) {
  return (
    <blockquote
      className={styles.reasonCallout}
      aria-label="추천 이유"
    >
      <div className={styles.reasonBody}>
        <span className={styles.reasonLabel} aria-hidden="true">
          추천 이유
        </span>
        <p className={styles.reasonText}>{reason}</p>
      </div>
    </blockquote>
  );
}

/* ── Main component ── */

export default function RecommendationReasonCard({
  track,
}: RecommendationReasonCardProps): JSX.Element {
  const hasReason = track.reason != null && track.reason.trim().length > 0;

  return (
    <article
      className={styles.card}
      aria-label={`${track.title} — ${track.artist}`}
    >
      {/* Track row */}
      <div className={styles.trackRow}>
        <ArtPlaceholder />

        <div className={styles.trackInfo}>
          <span className={styles.trackTitle}>{track.title}</span>
          <span className={styles.trackArtist}>{track.artist}</span>
          <span className={styles.trackAlbum}>{track.album}</span>
        </div>

        <span
          className={styles.duration}
          aria-label={`재생 시간 ${formatDuration(track.duration_sec)}`}
        >
          {formatDuration(track.duration_sec)}
        </span>
      </div>

      {/* Divider */}
      <div className={styles.divider} aria-hidden="true" />

      {/* Reason section */}
      {hasReason ? (
        <ReasonCallout reason={track.reason as string} />
      ) : (
        <ReasonSkeleton />
      )}
    </article>
  );
}

/* ── Convenience list wrapper ── */

export function RecommendationReasonList({
  tracks,
}: {
  tracks: RecommendedTrack[];
}): JSX.Element {
  return (
    <ul className={styles.list} role="list" aria-label="추천 곡 및 이유 목록">
      {tracks.map((track, i) => (
        <li
          key={track.track_id}
          style={{ '--i': i } as React.CSSProperties}
        >
          <RecommendationReasonCard track={track} />
        </li>
      ))}
    </ul>
  );
}
