/**
 * usePlaybackLogger 훅 테스트 (#48, US-18).
 * 재생 수명주기 → playbackApi 이벤트 매핑(start/end/complete) 검증.
 */
import { renderHook, act } from '@testing-library/react';

import { usePlaybackLogger } from '../lib/usePlaybackLogger';
import { playbackApi } from '../lib/api';

jest.mock('../lib/api', () => ({
  playbackApi: jest.fn().mockResolvedValue(undefined),
}));

const mockPlaybackApi = playbackApi as jest.MockedFunction<typeof playbackApi>;

/** jsdom 은 HTMLMediaElement 재생을 구현하지 않으므로 Audio 를 대체한다. */
class FakeAudio {
  src = '';
  preload = '';
  currentTime = 0;
  duration = NaN;
  ended = false;
  onended: (() => void) | null = null;
  play = jest.fn(() => Promise.resolve());
  pause = jest.fn();
}

const audioInstances: FakeAudio[] = [];
const realAudio = global.Audio;

beforeEach(() => {
  audioInstances.length = 0;
  global.Audio = jest.fn(() => {
    const a = new FakeAudio();
    audioInstances.push(a);
    return a;
  }) as unknown as typeof Audio;
});

afterEach(() => {
  global.Audio = realAudio;
  jest.clearAllMocks();
});

const TRACK = { trackId: 't-1', previewUrl: 'https://cdn.example/p1.mp3' };
const TRACK2 = { trackId: 't-2', previewUrl: 'https://cdn.example/p2.mp3' };

/** play() Promise 의 .then(start 로깅) 플러시. */
async function flush() {
  await act(async () => {});
}

describe('usePlaybackLogger', () => {
  it('재생 시작 → start 이벤트 로깅 + playingId 설정', async () => {
    const { result } = renderHook(() => usePlaybackLogger());

    act(() => result.current.toggle(TRACK));
    await flush();

    expect(result.current.playingId).toBe('t-1');
    expect(audioInstances[0].src).toBe(TRACK.previewUrl);
    expect(audioInstances[0].play).toHaveBeenCalled();
    expect(mockPlaybackApi).toHaveBeenCalledWith('t-1', 'start', undefined);
  });

  it('같은 곡 재토글(일시정지) → end 이벤트 + playback_pct 기록', async () => {
    const { result } = renderHook(() => usePlaybackLogger());

    act(() => result.current.toggle(TRACK));
    await flush();

    // 30초 중 15초 재생 지점에서 일시정지
    audioInstances[0].currentTime = 15;
    audioInstances[0].duration = 30;
    act(() => result.current.toggle(TRACK));

    expect(mockPlaybackApi).toHaveBeenCalledWith('t-1', 'end', 50);
    expect(audioInstances[0].pause).toHaveBeenCalled();
    expect(result.current.playingId).toBeNull();
  });

  it('끝까지 재생(ended) → complete 이벤트 + 100%', async () => {
    const { result } = renderHook(() => usePlaybackLogger());

    act(() => result.current.toggle(TRACK));
    await flush();

    act(() => {
      audioInstances[0].ended = true;
      audioInstances[0].onended?.();
    });

    expect(mockPlaybackApi).toHaveBeenCalledWith('t-1', 'complete', 100);
    expect(result.current.playingId).toBeNull();
  });

  it('다른 곡으로 전환 → 이전 곡 end 후 새 곡 start', async () => {
    const { result } = renderHook(() => usePlaybackLogger());

    act(() => result.current.toggle(TRACK));
    await flush();

    audioInstances[0].currentTime = 6;
    audioInstances[0].duration = 30;
    act(() => result.current.toggle(TRACK2));
    await flush();

    expect(mockPlaybackApi).toHaveBeenCalledWith('t-1', 'end', 20);
    expect(mockPlaybackApi).toHaveBeenCalledWith('t-2', 'start', undefined);
    expect(result.current.playingId).toBe('t-2');
  });

  it('previewUrl 없는 곡 → 재생/로깅 모두 미수행', () => {
    const { result } = renderHook(() => usePlaybackLogger());

    act(() => result.current.toggle({ trackId: 't-x', previewUrl: null }));

    expect(result.current.playingId).toBeNull();
    expect(audioInstances).toHaveLength(0);
    expect(mockPlaybackApi).not.toHaveBeenCalled();
  });

  it('언마운트(페이지 이탈) → 재생 중이던 곡 end 기록', async () => {
    const { result, unmount } = renderHook(() => usePlaybackLogger());

    act(() => result.current.toggle(TRACK));
    await flush();

    audioInstances[0].currentTime = 3;
    audioInstances[0].duration = 30;
    unmount();

    expect(mockPlaybackApi).toHaveBeenCalledWith('t-1', 'end', 10);
    expect(audioInstances[0].pause).toHaveBeenCalled();
  });

  it('duration 미확정(NaN) 시 end 의 playback_pct 는 undefined', async () => {
    const { result } = renderHook(() => usePlaybackLogger());

    act(() => result.current.toggle(TRACK));
    await flush();

    // duration = NaN (기본값) 그대로 일시정지
    act(() => result.current.toggle(TRACK));

    expect(mockPlaybackApi).toHaveBeenCalledWith('t-1', 'end', undefined);
  });

  it('play() 실패(autoplay 차단) → 상태 롤백 + start 미기록', async () => {
    const { result } = renderHook(() => usePlaybackLogger());

    // 첫 인스턴스 생성 전에 play 가 거부되도록 Audio mock 교체
    global.Audio = jest.fn(() => {
      const a = new FakeAudio();
      a.play = jest.fn(() => Promise.reject(new Error('NotAllowedError')));
      audioInstances.push(a);
      return a;
    }) as unknown as typeof Audio;

    act(() => result.current.toggle(TRACK));
    await flush();

    expect(result.current.playingId).toBeNull();
    expect(mockPlaybackApi).not.toHaveBeenCalledWith('t-1', 'start', undefined);
  });
});
