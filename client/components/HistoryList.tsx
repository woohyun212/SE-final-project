/**
 * HistoryList.tsx — 추천 이력 목록 컴포넌트 (#50, US-20).
 *
 * props-only. 상태는 각 항목의 펼침 토글만 로컬로 관리.
 * 상세 패널은 해당 세션의 추천 곡 전체(recommended_tracks, rank 순)를 보여주고,
 * 사용자가 남긴 피드백(feedbacks)은 곡별 배지로 매핑해 표시한다.
 */

import { useState } from 'react';
import type { HistoryItem, RecommendedTrackEntry } from '../lib/recommend';
import styles from '../styles/history.module.css';

// ── Helpers ──────────────────────────────────────────────────────────────────

/** ISO 8601 → 사람 읽기 편한 날짜+시간 (예: 2026년 6월 3일 오후 2:30) */
function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

/** 0..1 float → 퍼센트 문자열 (소수점 0자리) */
function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

/** feedback_type → 배지 className + 라벨 */
function feedbackBadgeProps(type: string): { className: string; label: string } {
  if (type === 'like') return { className: styles.badgeLike, label: '좋아요' };
  if (type === 'dislike') return { className: styles.badgeDislike, label: '싫어요' };
  return { className: styles.badgeNeutral, label: type };
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface RecommendedRowProps {
  entry: RecommendedTrackEntry;
  /** 해당 곡에 사용자가 남긴 피드백 (없으면 배지 미표시). */
  feedbackType?: string;
}

function RecommendedTrackRow({ entry, feedbackType }: RecommendedRowProps) {
  const badge = feedbackType ? feedbackBadgeProps(feedbackType) : null;
  return (
    <li className={styles.feedbackRow}>
      <span className={styles.rank} aria-hidden="true">
        {entry.rank}
      </span>
      <div className={styles.feedbackTrackInfo}>
        <span className={styles.feedbackTitle}>{entry.title}</span>
        <span className={styles.feedbackArtist}>{entry.artist}</span>
      </div>
      {badge && (
        <span
          className={`${styles.badge} ${badge.className}`}
          aria-label={`피드백: ${badge.label}`}
        >
          {badge.label}
        </span>
      )}
    </li>
  );
}

interface HistoryItemCardProps {
  item: HistoryItem;
  index: number;
}

function HistoryItemCard({ item, index }: HistoryItemCardProps) {
  const [open, setOpen] = useState(false);

  const trackCount = item.recommended_tracks.length;
  const feedbackCount = item.feedbacks.length;
  const feedbackByTrack = new Map(
    item.feedbacks.map((f) => [f.track_id, f.feedback_type]),
  );
  const sortedTracks = [...item.recommended_tracks].sort(
    (a, b) => a.rank - b.rank,
  );
  const sessionLabel =
    `추천 ${trackCount}곡` +
    (feedbackCount > 0 ? ` · 피드백 ${feedbackCount}` : '');

  return (
    <li
      className={styles.itemCard}
      style={{ '--i': index } as React.CSSProperties}
    >
      <button
        type="button"
        className={styles.summaryBtn}
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-controls={`history-detail-${item.id}`}
      >
        {/* date + subtitle */}
        <div className={styles.sessionMeta}>
          <span className={styles.sessionDate}>{formatDate(item.created_at)}</span>
          <span className={styles.sessionSubtitle}>{sessionLabel}</span>
        </div>

        {/* emotion coordinate pill */}
        <div
          className={styles.coordPill}
          aria-label={`감정 좌표 — 긍정도 ${pct(item.user_valence)}, 활기도 ${pct(item.user_energy)}`}
        >
          <span className={styles.coordDot} aria-hidden="true" />
          V {pct(item.user_valence)} · E {pct(item.user_energy)}
        </div>

        {/* chevron */}
        <span
          className={`${styles.chevron}${open ? ` ${styles.chevronOpen}` : ''}`}
          aria-hidden="true"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path
              d="M4 6l4 4 4-4"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </button>

      {/* detail panel — recommended tracks (rank 순) + 피드백 배지 */}
      {open && (
        <div
          id={`history-detail-${item.id}`}
          className={styles.detailPanel}
          role="region"
          aria-label="이 세션의 추천 곡"
        >
          <p className={styles.detailLabel}>이 세션의 추천 곡</p>
          {trackCount > 0 ? (
            <ul className={styles.feedbackList} aria-label="추천 곡 목록">
              {sortedTracks.map((t) => (
                <RecommendedTrackRow
                  key={t.track_id}
                  entry={t}
                  feedbackType={feedbackByTrack.get(t.track_id)}
                />
              ))}
            </ul>
          ) : (
            <p className={styles.noFeedback}>추천 곡이 없습니다.</p>
          )}
        </div>
      )}
    </li>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function HistoryListSkeleton() {
  return (
    <ul className={styles.skeletonList} aria-label="이력 불러오는 중" aria-busy="true">
      {[0, 1, 2].map((i) => (
        <li
          key={i}
          className={styles.skeletonCard}
          style={{ '--i': i } as React.CSSProperties}
        >
          <div className={styles.skeletonLines}>
            <div className={styles.skeletonLine} />
            <div className={styles.skeletonLine} />
          </div>
          <div className={styles.skeletonPill} />
        </li>
      ))}
    </ul>
  );
}

// ── Public component ──────────────────────────────────────────────────────────

export interface HistoryListProps {
  items: HistoryItem[];
  loading?: boolean;
  error?: string | null;
}

export default function HistoryList({ items, loading, error }: HistoryListProps) {
  if (loading) {
    return <HistoryListSkeleton />;
  }

  if (error) {
    return (
      <div className={styles.errorAlert} role="alert">
        <svg
          className={styles.errorIcon}
          width="18"
          height="18"
          viewBox="0 0 20 20"
          fill="none"
          aria-hidden="true"
        >
          <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="1.5" />
          <path
            d="M10 6v4M10 13.5v.5"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </svg>
        <span>{error}</span>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className={styles.emptyState} role="status">
        <svg
          className={styles.emptyIcon}
          width="48"
          height="48"
          viewBox="0 0 48 48"
          fill="none"
          aria-hidden="true"
        >
          <rect
            x="8"
            y="12"
            width="32"
            height="28"
            rx="4"
            stroke="currentColor"
            strokeWidth="2"
          />
          <path
            d="M16 20h16M16 27h10"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="36" cy="12" r="6" fill="currentColor" opacity="0.25" />
        </svg>
        <p className={styles.emptyTitle}>추천 이력이 없습니다.</p>
        <p className={styles.emptySubtitle}>
          음악을 추천받은 세션이 여기에 표시됩니다.
        </p>
      </div>
    );
  }

  return (
    <ul className={styles.list} aria-label="추천 이력 목록">
      {items.map((item, i) => (
        <HistoryItemCard key={item.id} item={item} index={i} />
      ))}
    </ul>
  );
}
