/**
 * AudioPlayer.tsx — 곡 행 미리듣기 재생/일시정지 버튼 (#48, US-18).
 *
 * props-only 프레젠테이션 컴포넌트. 실제 재생/로깅은 usePlaybackLogger 훅이
 * 담당하고, 이 컴포넌트는 상태 표시와 토글 이벤트만 처리한다.
 * preview_url 이 없는 곡(현재 카탈로그 전곡)은 비활성 상태로 사유를 안내한다.
 */

import styles from '../styles/player.module.css';

export interface AudioPlayerProps {
  /** 30초 미리듣기 URL. 없으면 버튼 비활성. */
  previewUrl?: string | null;
  /** 이 곡이 현재 재생 중인지. */
  playing: boolean;
  /** 재생/일시정지 토글 콜백. */
  onToggle: () => void;
}

function PlayIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
      <path d="M8 5v14l11-7L8 5Z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
      <path d="M6 5h4v14H6V5Zm8 0h4v14h-4V5Z" />
    </svg>
  );
}

export default function AudioPlayer({ previewUrl, playing, onToggle }: AudioPlayerProps) {
  const disabled = !previewUrl;
  const label = disabled
    ? '미리듣기가 제공되지 않는 곡입니다'
    : playing
      ? '일시정지'
      : '미리듣기 재생';

  return (
    <button
      type="button"
      className={`${styles.playBtn}${playing ? ` ${styles.playing}` : ''}`}
      onClick={onToggle}
      disabled={disabled}
      aria-pressed={playing}
      aria-label={label}
      title={label}
    >
      {playing ? <PauseIcon /> : <PlayIcon />}
    </button>
  );
}
