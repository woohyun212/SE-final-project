/**
 * trackEnrichment 단위 테스트 (FR5.4 / FR5.2).
 *
 * iTunes Search API 호출을 fetch mock 으로 대체해
 * 정상 보강(앨범아트 512 업스케일) · 결과 0 · 네트워크 오류 · 캐시 재사용을 검증한다.
 */
import { enrichTrack, __clearEnrichmentCache } from '../lib/trackEnrichment';

const realFetch = global.fetch;

afterEach(() => {
  global.fetch = realFetch;
  __clearEnrichmentCache();
  jest.clearAllMocks();
});

describe('enrichTrack', () => {
  it('정상 응답 → previewUrl + artworkUrl(512 업스케일) 반환', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        resultCount: 1,
        results: [
          {
            previewUrl: 'https://audio.itunes/p1.m4a',
            artworkUrl100: 'https://art.itunes/a/100x100bb.jpg',
          },
        ],
      }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const res = await enrichTrack('Yesterday', 'The Beatles');

    expect(res.previewUrl).toBe('https://audio.itunes/p1.m4a');
    // 100x100 → 512x512 업스케일
    expect(res.artworkUrl).toBe('https://art.itunes/a/512x512bb.jpg');

    // term 에 곡명+아티스트가 인코딩되어 들어가는지
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain('itunes.apple.com/search');
    expect(url).toContain(encodeURIComponent('Yesterday The Beatles'));
    expect(url).toContain('entity=song');
    expect(url).toContain('limit=1');
  });

  it('결과 0건 → {previewUrl:null, artworkUrl:null}', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ resultCount: 0, results: [] }),
    }) as unknown as typeof fetch;

    const res = await enrichTrack('Unknown Song', 'Nobody');
    expect(res).toEqual({ previewUrl: null, artworkUrl: null });
  });

  it('네트워크 throw → graceful null (throw 안 함)', async () => {
    global.fetch = jest
      .fn()
      .mockRejectedValue(new Error('network down')) as unknown as typeof fetch;

    const res = await enrichTrack('Song', 'Artist');
    expect(res).toEqual({ previewUrl: null, artworkUrl: null });
  });

  it('비-2xx 응답 → graceful null', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      json: async () => ({}),
    }) as unknown as typeof fetch;

    const res = await enrichTrack('Song', 'Artist');
    expect(res).toEqual({ previewUrl: null, artworkUrl: null });
  });

  it('빈 title/artist → fetch 호출 없이 null', async () => {
    const fetchMock = jest.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    const res = await enrichTrack('', 'Artist');
    expect(res).toEqual({ previewUrl: null, artworkUrl: null });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('동일 (title|artist) 재호출 → 캐시 사용(fetch 1회)', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        resultCount: 1,
        results: [
          {
            previewUrl: 'https://audio.itunes/p1.m4a',
            artworkUrl100: 'https://art.itunes/a/100x100bb.jpg',
          },
        ],
      }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    const a = await enrichTrack('Imagine', 'John Lennon');
    const b = await enrichTrack('Imagine', 'John Lennon');

    expect(a).toEqual(b);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('대소문자/공백 차이는 같은 캐시 키로 취급', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        resultCount: 1,
        results: [{ previewUrl: 'https://a/p.m4a', artworkUrl100: 'https://a/100x100.jpg' }],
      }),
    });
    global.fetch = fetchMock as unknown as typeof fetch;

    await enrichTrack('Imagine', 'John Lennon');
    await enrichTrack('  imagine ', 'JOHN LENNON');

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
