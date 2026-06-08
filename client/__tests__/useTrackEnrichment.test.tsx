/**
 * useTrackEnrichment 훅 테스트 (FR5.4 / FR5.2 / FR6.2).
 *
 * preview_url 이 있는 곡은 보강 skip, null 인 곡만 enrichTrack 호출,
 * track_id 키로 결과가 매핑되는지 검증한다.
 */
import { renderHook, waitFor } from '@testing-library/react';

import { useTrackEnrichment } from '../lib/useTrackEnrichment';
import { enrichTrack } from '../lib/trackEnrichment';

jest.mock('../lib/trackEnrichment', () => ({
  enrichTrack: jest.fn(),
}));

const mockEnrich = enrichTrack as jest.MockedFunction<typeof enrichTrack>;

afterEach(() => {
  jest.clearAllMocks();
});

describe('useTrackEnrichment', () => {
  it('preview_url 이 있는 곡은 보강하지 않고, null 인 곡만 enrichTrack 호출', async () => {
    mockEnrich.mockResolvedValue({
      previewUrl: 'https://itunes/p.m4a',
      artworkUrl: 'https://itunes/512.jpg',
    });

    const tracks = [
      { track_id: 'has-url', title: 'A', artist: 'X', preview_url: 'https://backend/p.mp3' },
      { track_id: 'null-url', title: 'B', artist: 'Y', preview_url: null },
    ];

    const { result } = renderHook(() => useTrackEnrichment(tracks));

    await waitFor(() => {
      expect(result.current['null-url']).toBeDefined();
    });

    // preview_url 이 있는 곡은 호출 대상 아님
    expect(mockEnrich).toHaveBeenCalledTimes(1);
    expect(mockEnrich).toHaveBeenCalledWith('B', 'Y', expect.anything());
    expect(mockEnrich).not.toHaveBeenCalledWith('A', 'X', expect.anything());
  });

  it('track_id 키로 보강 결과를 매핑한다', async () => {
    mockEnrich.mockResolvedValue({
      previewUrl: 'https://itunes/p2.m4a',
      artworkUrl: 'https://itunes/art2.jpg',
    });

    const tracks = [{ track_id: 'tk-99', title: 'Song', artist: 'Star', preview_url: null }];

    const { result } = renderHook(() => useTrackEnrichment(tracks));

    await waitFor(() => {
      expect(result.current['tk-99']).toEqual({
        previewUrl: 'https://itunes/p2.m4a',
        artworkUrl: 'https://itunes/art2.jpg',
      });
    });
  });

  it('보강 결과가 둘 다 null 이면 맵에 추가하지 않는다', async () => {
    mockEnrich.mockResolvedValue({ previewUrl: null, artworkUrl: null });

    const tracks = [{ track_id: 'tk-empty', title: 'C', artist: 'Z', preview_url: null }];

    const { result } = renderHook(() => useTrackEnrichment(tracks));

    // 보강 호출은 일어나되, null 결과는 맵에 반영되지 않음.
    await waitFor(() => expect(mockEnrich).toHaveBeenCalled());
    expect(result.current['tk-empty']).toBeUndefined();
  });

  it('track_id 가 없는 곡은 보강 대상에서 제외', async () => {
    mockEnrich.mockResolvedValue({ previewUrl: 'x', artworkUrl: 'y' });

    const tracks = [{ title: 'NoId', artist: 'Q', preview_url: null }];

    renderHook(() => useTrackEnrichment(tracks));

    // 마이크로태스크 플러시 후에도 호출되지 않아야 함.
    await Promise.resolve();
    expect(mockEnrich).not.toHaveBeenCalled();
  });
});
