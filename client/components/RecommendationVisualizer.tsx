/**
 * RecommendationVisualizer.tsx — 추천 결과 리스트 컴포넌트
 *
 * Props-only component (no API calls, no routing).
 * Renders tracks, loading skeletons, error alert, or empty state.
 *
 * Track type is defined locally here; structurally compatible with
 * the shape in client/lib/api.ts (defined independently per task spec).
 */

import { useState } from 'react';

import styles from '../styles/recommend.module.css';

/* ── Public types ── */

export interface Track {
  /** 백엔드 track_id — 피드백/재생 API 연동 키 (#47/#48). 선택(하위호환). */
  track_id?: string;
  title: string;
  artist: string;
  album: string;
  duration_sec: number;
  /** 30초 미리듣기 URL — 재생 버튼 활성 조건 (#48). 선택(하위호환). */
  preview_url?: string | null;
  /** 앨범아트 URL — iTunes 보강(FR5.2). 없으면 음악노트 placeholder. 선택(하위호환). */
  artwork_url?: string | null;
}

export interface RecommendationVisualizerProps {
  tracks: Track[];
  loading: boolean;
  error?: string | null;
  /** 곡 행 우측에 액션(피드백 버튼/재생 컨트롤 등)을 주입하는 슬롯 (#47/#48). */
  renderRowActions?: (track: Track) => React.ReactNode;
}

/* ── Helpers ── */

/** Format seconds as m:ss — e.g. 480 → "8:00", 75 → "1:15" */
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
      {/* music note icon — inline SVG, no external dependency */}
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

/**
 * 앨범아트 — artwork_url(iTunes 보강, FR5.2) 있으면 <img>, 없으면 음악노트 placeholder.
 * 이미지 로드 실패(onError) 시 placeholder 로 graceful fallback.
 */
function AlbumArt({ src, title }: { src?: string | null; title: string }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <ArtPlaceholder />;
  }

  return (
    <img
      className={styles.artImage}
      src={src}
      alt={`${title} 앨범 커버`}
      width={64}
      height={64}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  );
}

/** Single shimmer skeleton row */
function SkeletonRow({ index }: { index: number }) {
  return (
    <li
      className={styles.skeletonItem}
      style={{ '--i': index } as React.CSSProperties}
      aria-hidden="true"
    >
      <div className={styles.skeletonArt} />
      <div className={styles.skeletonLines}>
        <div className={styles.skeletonLine} />
        <div className={styles.skeletonLine} />
        <div className={styles.skeletonLine} />
      </div>
      <div className={styles.skeletonDuration} />
    </li>
  );
}

/** 5-row loading skeleton */
function LoadingSkeleton() {
  return (
    <ul className={styles.skeletonList} aria-label="추천 곡을 불러오는 중…">
      {Array.from({ length: 5 }, (_, i) => (
        <SkeletonRow key={i} index={i} />
      ))}
    </ul>
  );
}

/** Error alert box */
function ErrorAlert({ message }: { message: string }) {
  return (
    <div className={styles.errorAlert} role="alert">
      <span className={styles.errorIcon} aria-hidden="true">
        {/* warning triangle SVG */}
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M12 2 1 21h22L12 2Zm0 3.5L21 20H3L12 5.5ZM11 10v4h2v-4h-2Zm0 6v2h2v-2h-2Z" />
        </svg>
      </span>
      {message}
    </div>
  );
}

/** Empty state */
function EmptyState() {
  return (
    <div className={styles.emptyState}>
      <span className={styles.emptyIcon} aria-hidden="true">
        {/* music-off / queue-music icon */}
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M15 6H9v2h6V6ZM9 10v2h4v-2H9Zm10-7H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2Zm0 16H5V5h14v14Z" />
        </svg>
      </span>
      <p className={styles.emptyTitle}>추천 결과가 없습니다.</p>
      <p className={styles.emptySubtitle}>감정을 입력하면 어울리는 곡을 추천해 드립니다.</p>
    </div>
  );
}

/** Single track row */
function TrackRow({
  track,
  index,
  renderRowActions,
}: {
  track: Track;
  index: number;
  renderRowActions?: (track: Track) => React.ReactNode;
}) {
  return (
    <li
      className={styles.trackItem}
      style={{ '--i': index } as React.CSSProperties}
    >
      <AlbumArt src={track.artwork_url} title={track.title} />
      <div className={styles.trackInfo}>
        <span className={styles.trackTitle}>{track.title}</span>
        <span className={styles.trackArtist}>{track.artist}</span>
        <span className={styles.trackAlbum}>{track.album}</span>
      </div>
      <span className={styles.duration} aria-label={`재생 시간 ${formatDuration(track.duration_sec)}`}>
        {formatDuration(track.duration_sec)}
      </span>
      {renderRowActions && (
        <div className={styles.rowActions}>{renderRowActions(track)}</div>
      )}
    </li>
  );
}

/* ── Main component ── */

export default function RecommendationVisualizer({
  tracks,
  loading,
  error,
  renderRowActions,
}: RecommendationVisualizerProps): JSX.Element {
  /* Loading state */
  if (loading) {
    return (
      <div className={styles.container} aria-busy={true} aria-label="추천 곡을 불러오는 중…">
        <LoadingSkeleton />
      </div>
    );
  }

  /* Error state */
  if (error) {
    return (
      <div className={styles.container} aria-busy={false}>
        <ErrorAlert message={error} />
      </div>
    );
  }

  /* Empty state */
  if (tracks.length === 0) {
    return (
      <div className={styles.container} aria-busy={false}>
        <EmptyState />
      </div>
    );
  }

  /* Track list */
  return (
    <div className={styles.container} aria-busy={false}>
      <ul className={styles.list} role="list" aria-label="추천 곡 목록">
        {tracks.map((track, i) => (
          <TrackRow
            key={`${track.title}-${track.artist}-${i}`}
            track={track}
            index={i}
            renderRowActions={renderRowActions}
          />
        ))}
      </ul>
    </div>
  );
}
