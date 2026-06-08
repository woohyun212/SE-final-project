/**
 * useTrackEnrichment.ts — 추천 곡 리스트의 미리듣기/앨범아트 lazy 보강 훅 (FR5.4 / FR5.2 / FR6.2).
 *
 * 백엔드가 preview_url 을 채우면 그 값을 우선하고, null 인 곡만 마운트 후
 * 클라이언트에서 iTunes Search API 로 보강한다. SSR 환경에서는 동작하지 않는다.
 *
 * 정책:
 *   - preview_url 이 이미 있는 곡은 보강 생략(백엔드 우선).
 *   - track_id 를 키로 결과 맵을 반환 — 호출부에서 곡별 병합.
 *   - 곡당 1회만 보강 (이미 시도한 키는 재요청하지 않음 → 과도호출 방지).
 *   - 언마운트 시 진행 중 요청 abort (메모리/네트워크 누수 방지).
 */

import { useEffect, useRef, useState } from 'react';

import { enrichTrack, type TrackEnrichment } from './trackEnrichment';

/** 보강 대상 곡의 최소 정보 — RecommendedTrack / Track 와 구조적 호환. */
export interface EnrichableTrack {
  track_id?: string;
  title: string;
  artist: string;
  preview_url?: string | null;
}

/**
 * preview_url 이 없는 곡만 클라이언트에서 보강하고, track_id → 보강결과 맵을 반환.
 *
 * 반환 맵은 보강이 도착할 때마다 점진적으로 채워진다. 호출부는
 * `track.preview_url ?? map[id]?.previewUrl`, `map[id]?.artworkUrl` 형태로 병합한다.
 */
export function useTrackEnrichment(
  tracks: EnrichableTrack[],
): Record<string, TrackEnrichment> {
  const [enrichments, setEnrichments] = useState<Record<string, TrackEnrichment>>({});
  /** 이미 보강을 시도한 track_id 집합 — 곡당 1회 보장(중복 fetch 차단). */
  const attemptedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    // SSR 가드 — 브라우저에서만 보강(fetch/AbortController 의존).
    if (typeof window === 'undefined') return;

    const controller = new AbortController();

    for (const track of tracks) {
      const id = track.track_id;
      // track_id 없거나 / 백엔드 preview_url 이미 있거나 / 이미 시도한 곡은 skip.
      if (!id) continue;
      if (track.preview_url) continue;
      if (attemptedRef.current.has(id)) continue;

      attemptedRef.current.add(id);

      void enrichTrack(track.title, track.artist, controller.signal).then(
        (result) => {
          // abort 후 도착한 응답은 상태에 반영하지 않는다.
          if (controller.signal.aborted) return;
          // 둘 다 null 이면 UI 변화가 없으므로 맵을 갱신하지 않는다.
          if (!result.previewUrl && !result.artworkUrl) return;
          setEnrichments((prev) => ({ ...prev, [id]: result }));
        },
      );
    }

    // 언마운트/의존성 변경 시 진행 중 요청 취소.
    return () => controller.abort();
    // tracks 배열 자체보다 곡 식별/보강조건을 의존성으로 사용해 불필요 재실행을 줄인다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    tracks
      .map((t) => `${t.track_id ?? ''}:${t.preview_url ? 1 : 0}`)
      .join(','),
  ]);

  return enrichments;
}
