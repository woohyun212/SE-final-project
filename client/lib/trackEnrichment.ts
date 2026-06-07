/**
 * trackEnrichment.ts — iTunes Search API 기반 미리듣기 URL · 앨범아트 보강 (FR5.4 / FR5.2 / FR6.2).
 *
 * 배경: 백엔드 카탈로그(dataset.csv)에 preview_url · 앨범이미지 컬럼이 없어
 * 전곡 preview_url=null → 재생 불가 · 앨범아트 placeholder 고정 · 재생이벤트 미발화.
 * 백엔드/키 의존 없이 클라이언트에서 곡명+아티스트로 30초 미리듣기와 앨범아트를 보강한다.
 *
 * iTunes Search API (무인증 · CORS 허용 · 브라우저 직접 호출 가능):
 *   GET https://itunes.apple.com/search?term=<title+artist>&entity=song&limit=1
 *   → { resultCount, results: [{ previewUrl, artworkUrl100, trackName, artistName }] }
 *
 * 정책:
 *   - 네트워크/파싱 실패 · 타임아웃(8초) · 결과 0 → graceful null (throw 금지).
 *   - 앨범아트는 artworkUrl100 의 "100x100" → "512x512" 업스케일.
 *   - 동일 (title|artist) 키는 in-memory Map 으로 캐시 (중복 호출 방지).
 */

/** 한 곡의 보강 결과 — 둘 다 실패 시 null. */
export interface TrackEnrichment {
  /** 30초 미리듣기 m4a URL. 미발견/실패 시 null. */
  previewUrl: string | null;
  /** 512x512 앨범아트 URL. 미발견/실패 시 null. */
  artworkUrl: string | null;
}

/** iTunes Search API 응답에서 사용하는 필드만 추린 raw shape. */
interface ItunesResult {
  previewUrl?: string;
  artworkUrl100?: string;
}

interface ItunesResponse {
  resultCount?: number;
  results?: ItunesResult[];
}

const ITUNES_ENDPOINT = 'https://itunes.apple.com/search';
const TIMEOUT_MS = 8000;

/** (title|artist) → 보강 결과 in-memory 캐시. 같은 곡 재호출 시 네트워크 생략. */
const cache = new Map<string, TrackEnrichment>();

/** 둘 다 null 인 공용 빈 결과 — graceful fallback. */
const EMPTY: TrackEnrichment = { previewUrl: null, artworkUrl: null };

/** 캐시 키 — 대소문자/공백 정규화로 사소한 차이를 흡수. */
function cacheKey(title: string, artist: string): string {
  return `${title.trim().toLowerCase()}|${artist.trim().toLowerCase()}`;
}

/** artworkUrl100 → 512x512 업스케일. 패턴 불일치 시 원본 그대로. */
function upscaleArtwork(url100: string | undefined): string | null {
  if (!url100) return null;
  return url100.replace('100x100', '512x512');
}

/**
 * 곡명 + 아티스트로 iTunes 에서 미리듣기 URL · 앨범아트를 조회한다.
 *
 * 실패(네트워크/파싱/타임아웃/결과 0)는 throw 하지 않고 `{previewUrl:null, artworkUrl:null}` 반환.
 * 동일 키는 캐시에서 즉시 반환한다. 호출자가 넘긴 `signal` 로 외부 취소도 가능.
 */
export async function enrichTrack(
  title: string,
  artist: string,
  signal?: AbortSignal,
): Promise<TrackEnrichment> {
  // 빈 입력은 조회 의미가 없으므로 즉시 빈 결과.
  if (!title || !artist) return EMPTY;

  const key = cacheKey(title, artist);
  const cached = cache.get(key);
  if (cached) return cached;

  // 8초 타임아웃 — 호출자 signal 과 내부 timeout 중 먼저 발화하는 쪽이 abort.
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const onExternalAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener('abort', onExternalAbort);
  }

  try {
    const term = encodeURIComponent(`${title} ${artist}`);
    const url = `${ITUNES_ENDPOINT}?term=${term}&entity=song&limit=1`;

    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) return EMPTY;

    const data = (await res.json()) as ItunesResponse;
    const first = data.results?.[0];
    if (!first) return EMPTY;

    const enrichment: TrackEnrichment = {
      previewUrl: first.previewUrl ?? null,
      artworkUrl: upscaleArtwork(first.artworkUrl100),
    };
    // 성공 결과만 캐시 — 일시적 실패는 다음 호출에서 재시도되도록 캐시하지 않는다.
    cache.set(key, enrichment);
    return enrichment;
  } catch {
    // 네트워크 오류 · abort · JSON 파싱 실패 모두 graceful null.
    return EMPTY;
  } finally {
    clearTimeout(timer);
    if (signal) signal.removeEventListener('abort', onExternalAbort);
  }
}

/** 테스트 격리용 — 캐시 초기화. */
export function __clearEnrichmentCache(): void {
  cache.clear();
}
