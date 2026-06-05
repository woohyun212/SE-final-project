/**
 * usePlaybackLogger.ts — 미리듣기 재생 + 재생 이벤트 로깅 훅 (#48, US-18).
 *
 * 단일 공유 HTMLAudioElement 로 한 번에 한 곡만 재생하고, 재생 수명주기를
 * 백엔드 `POST /feedback/playback` (playbackApi) 으로 기록한다 (FR6.2).
 *
 * 이벤트 매핑:
 * - play 성공          → 'start'
 * - 끝까지 재생(ended) → 'complete' (playback_pct=100)
 * - 일시정지/곡 전환/언마운트 → 'end' (playback_pct = currentTime/duration×100)
 *
 * 로깅은 fire-and-forget — 실패해도 재생 UX 를 막지 않는다.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { playbackApi } from './api';
import type { PlaybackEvent } from './recommend';

/** toggle() 입력 — 재생에 필요한 최소 트랙 정보. */
export interface PlayableTrack {
  trackId: string;
  previewUrl: string | null;
}

/** 로깅 실패는 조용히 무시 (UX 비차단). */
function logSafe(trackId: string, event: PlaybackEvent, pct?: number): void {
  void playbackApi(trackId, event, pct).catch(() => {
    // ignore — 재생 이벤트 로깅 실패가 재생을 막아선 안 된다.
  });
}

/** 현재 재생 위치를 0..100 퍼센트로. duration 미확정 시 undefined. */
function pctOf(audio: HTMLAudioElement): number | undefined {
  if (!audio.duration || !Number.isFinite(audio.duration)) return undefined;
  const pct = (audio.currentTime / audio.duration) * 100;
  return Math.min(100, Math.round(pct * 10) / 10);
}

export interface PlaybackController {
  /** 현재 재생 중인 track_id (없으면 null). */
  playingId: string | null;
  /** 재생/일시정지 토글. 다른 곡 재생 중이면 그 곡을 'end' 처리 후 전환. */
  toggle: (track: PlayableTrack) => void;
}

export function usePlaybackLogger(): PlaybackController {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentIdRef = useRef<string | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);

  /** 현재 곡 정지. ended 직후가 아니면 'end' 이벤트를 남긴다. */
  const stopCurrent = useCallback(() => {
    const audio = audioRef.current;
    const id = currentIdRef.current;
    if (!audio || !id) return;
    if (!audio.ended) {
      logSafe(id, 'end', pctOf(audio));
    }
    audio.pause();
    currentIdRef.current = null;
    setPlayingId(null);
  }, []);

  const toggle = useCallback(
    (track: PlayableTrack) => {
      // 같은 곡 → 일시정지(end 기록)
      if (currentIdRef.current === track.trackId) {
        stopCurrent();
        return;
      }
      // 다른 곡 재생 중이었다면 먼저 end 처리
      stopCurrent();

      if (!track.trackId || !track.previewUrl) return;

      let audio = audioRef.current;
      if (!audio) {
        audio = new Audio();
        audio.preload = 'none';
        // 끝까지 재생 → complete (100%). 단일 핸들러가 currentIdRef 를 참조.
        audio.onended = () => {
          const endedId = currentIdRef.current;
          if (endedId) logSafe(endedId, 'complete', 100);
          currentIdRef.current = null;
          setPlayingId(null);
        };
        audioRef.current = audio;
      }

      audio.src = track.previewUrl;
      currentIdRef.current = track.trackId;
      setPlayingId(track.trackId);

      void audio
        .play()
        .then(() => logSafe(track.trackId, 'start'))
        .catch(() => {
          // autoplay 차단/소스 오류 — 재생 상태 롤백, start 미기록.
          if (currentIdRef.current === track.trackId) {
            currentIdRef.current = null;
            setPlayingId(null);
          }
        });
    },
    [stopCurrent],
  );

  // 페이지 이탈(언마운트) 시 재생 중이던 곡을 end 처리.
  useEffect(() => stopCurrent, [stopCurrent]);

  return { playingId, toggle };
}
