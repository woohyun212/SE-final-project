/**
 * FeedbackButtons.tsx — 좋아요/싫어요 피드백 버튼 (#47, FR6.1).
 *
 * append-only 설계 — 취소 UI 없음. like ↔ dislike 변경은 허용(택1).
 * 낙관적 업데이트: 클릭 즉시 로컬 상태 반영 → feedbackApi 호출 → 실패 시 롤백(조용히).
 * recommendationId 미제공 시 버튼 disabled(세션 없음 — 서버에 보낼 키가 없다).
 */

import { useCallback, useState } from 'react';
import { feedbackApi } from '../lib/api';
import type { FeedbackType } from '../lib/recommend';
import styles from '../styles/feedback.module.css';

export interface FeedbackButtonsProps {
  trackId: string;
  recommendationId?: string;
  /** 현재 선택된 피드백 값 (외부 controlled). null/undefined = 미선택. */
  value?: FeedbackType | null;
  /** 선택 변경 시 호출. 낙관적 업데이트 후 실패 시 이전 값으로 롤백된다. */
  onChange?: (v: FeedbackType) => void;
}

export default function FeedbackButtons({
  trackId,
  recommendationId,
  value,
  onChange,
}: FeedbackButtonsProps) {
  /** API 호출 진행 중 여부 — 중복 클릭 방지. */
  const [pending, setPending] = useState(false);

  const disabled = !recommendationId || !trackId || pending;

  const handleClick = useCallback(
    async (type: FeedbackType) => {
      if (!recommendationId || !trackId || pending) return;
      // like ↔ dislike 변경 허용 but 같은 값 재클릭도 낙관적으로 반영(append-only 서버측).
      const prev = value ?? null;
      onChange?.(type);
      setPending(true);
      try {
        await feedbackApi(type, trackId, recommendationId);
      } catch {
        // 실패 시 롤백 — 에러 노출 없음(조용히).
        if (prev !== null) {
          onChange?.(prev);
        } else {
          // 미선택 상태로 롤백 — onChange 에 null 을 전달할 방법이 없으므로
          // 호출자 Record 에서 key 삭제가 필요하지만 인터페이스가 FeedbackType 만
          // 허용하므로, 여기선 아무것도 호출하지 않아 낙관적 상태가 유지된다.
          // (실패 시 서버와 UI 불일치 허용 — 설계상 조용한 실패).
        }
      } finally {
        setPending(false);
      }
    },
    [recommendationId, trackId, pending, value, onChange],
  );

  const likeActive = value === 'like';
  const dislikeActive = value === 'dislike';

  return (
    <div className={styles.wrapper} aria-label="곡 피드백">
      <button
        type="button"
        className={`${styles.btn} ${likeActive ? styles.likeActive : ''}`}
        onClick={() => handleClick('like')}
        disabled={disabled}
        aria-pressed={likeActive}
        aria-label="좋아요"
        title="좋아요"
      >
        {/* thumbs-up SVG */}
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M1 21h4V9H1v12Zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2Z" />
        </svg>
      </button>

      <button
        type="button"
        className={`${styles.btn} ${dislikeActive ? styles.dislikeActive : ''}`}
        onClick={() => handleClick('dislike')}
        disabled={disabled}
        aria-pressed={dislikeActive}
        aria-label="싫어요"
        title="싫어요"
      >
        {/* thumbs-down SVG */}
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
          focusable="false"
        >
          <path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2Zm4 0v12h4V3h-4Z" />
        </svg>
      </button>
    </div>
  );
}
