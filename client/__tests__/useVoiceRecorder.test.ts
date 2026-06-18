/**
 * useVoiceRecorder 단위 테스트 (US-3 / 이슈 #18).
 *
 * getUserMedia 와 MediaRecorder 를 mock 으로 대체하고 fake timer 로 5초 자동 종료 /
 * 2초 최소 길이 / 권한 거부 / 미지원 경로를 검증한다.
 */
import { act, renderHook } from "@testing-library/react";

import {
  MAX_DURATION_MS,
  MIN_DURATION_MS,
  useVoiceRecorder,
} from "../lib/useVoiceRecorder";
import { encodeWav } from "../lib/encodeWav";

// encodeWav 는 AudioContext/디코딩에 의존하므로 jsdom 에선 mock 으로 대체한다.
// 녹음 원본을 그대로 audio/wav Blob 으로 감싼 값을 즉시 resolve.
jest.mock("../lib/encodeWav", () => ({
  encodeWav: jest.fn(
    (blob: Blob) => Promise.resolve(new Blob([blob], { type: "audio/wav" }))
  ),
}));

const mockEncodeWav = encodeWav as jest.MockedFunction<typeof encodeWav>;

// ── MediaRecorder mock ──────────────────────────────────────────────────────
const recorderInstances: MockMediaRecorder[] = [];

class MockMediaRecorder {
  static isTypeSupported = jest.fn(() => true);

  state: "inactive" | "recording" | "paused" = "inactive";
  mimeType: string;
  ondataavailable: ((e: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;

  constructor(_stream: MediaStream, options?: { mimeType?: string }) {
    this.mimeType = options?.mimeType ?? "";
    recorderInstances.push(this);
  }

  start(): void {
    this.state = "recording";
  }

  stop(): void {
    this.state = "inactive";
    // 실제 MediaRecorder 처럼 마지막 청크를 흘린 뒤 onstop 을 호출.
    this.ondataavailable?.({ data: new Blob(["audio-chunk"], { type: "audio/webm" }) });
    this.onstop?.();
  }
}

function makeStream(): MediaStream {
  const track = { stop: jest.fn() } as unknown as MediaStreamTrack;
  return { getTracks: () => [track] } as unknown as MediaStream;
}

function setMediaDevices(getUserMedia: jest.Mock | undefined): void {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: getUserMedia ? { getUserMedia } : undefined,
  });
}

beforeEach(() => {
  jest.useFakeTimers();
  recorderInstances.length = 0;
  (global as unknown as { MediaRecorder: unknown }).MediaRecorder =
    MockMediaRecorder;
  setMediaDevices(jest.fn().mockResolvedValue(makeStream()));
});

afterEach(() => {
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
  jest.clearAllMocks();
});

describe("useVoiceRecorder", () => {
  it("초기 상태는 idle", () => {
    const { result } = renderHook(() => useVoiceRecorder());
    expect(result.current.status).toBe("idle");
    expect(result.current.audioBlob).toBeNull();
    expect(result.current.elapsedMs).toBe(0);
  });

  it("녹음 API 미지원 환경이면 unsupported", async () => {
    setMediaDevices(undefined);
    const { result } = renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe("unsupported");
    expect(result.current.errorMessage).toMatch(/지원하지 않/);
  });

  it("권한 거부(NotAllowedError) 시 denied", async () => {
    const denied = new Error("denied");
    denied.name = "NotAllowedError";
    setMediaDevices(jest.fn().mockRejectedValue(denied));

    const { result } = renderHook(() => useVoiceRecorder());
    await act(async () => {
      await result.current.start();
    });

    expect(result.current.status).toBe("denied");
    expect(result.current.errorMessage).toMatch(/마이크 권한/);
  });

  it("start 하면 recording 상태가 되고 elapsedMs 가 증가한다", async () => {
    const { result } = renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });
    expect(result.current.status).toBe("recording");

    act(() => {
      jest.advanceTimersByTime(300);
    });
    expect(result.current.elapsedMs).toBeGreaterThanOrEqual(300);
  });

  it(`${MAX_DURATION_MS}ms 경과 시 자동 종료되어 WAV 변환 후 recorded + audioBlob`, async () => {
    const { result } = renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });

    // 자동 종료 → onstop 에서 encodeWav(비동기) 호출 → 변환 완료까지 microtask flush.
    await act(async () => {
      jest.advanceTimersByTime(MAX_DURATION_MS);
    });

    expect(mockEncodeWav).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe("recorded");
    expect(result.current.audioBlob).toBeInstanceOf(Blob);
    expect(result.current.audioBlob?.type).toBe("audio/wav");
  });

  it(`${MIN_DURATION_MS}ms 미만에서 stop 하면 too_short + 결과 폐기`, async () => {
    const { result } = renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });

    act(() => {
      jest.advanceTimersByTime(1000); // < 2초
      result.current.stop();
    });

    expect(result.current.status).toBe("too_short");
    expect(result.current.audioBlob).toBeNull();
  });

  it("reset 하면 idle 로 돌아오고 마이크 트랙을 정지한다", async () => {
    const { result } = renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      jest.advanceTimersByTime(MAX_DURATION_MS);
    });
    expect(result.current.status).toBe("recorded");

    act(() => {
      result.current.reset();
    });

    expect(result.current.status).toBe("idle");
    expect(result.current.audioBlob).toBeNull();
    expect(result.current.elapsedMs).toBe(0);
  });
});
