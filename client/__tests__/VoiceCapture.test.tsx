/**
 * VoiceCapture 단위 테스트 (US-3 / 이슈 #18).
 *
 * useVoiceRecorder 훅과 recommendApi 를 mock 으로 대체하고, 각 녹음/업로드 상태에서
 * 올바른 안내·버튼·자동 업로드 동작이 렌더되는지 검증한다.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import VoiceCapture from "../components/VoiceCapture";
import { ApiError, recommendApi } from "../lib/api";
import { useVoiceRecorder, type VoiceRecorder } from "../lib/useVoiceRecorder";

// recommendApi 만 mock, ApiError 등 나머지는 실제 구현 유지.
jest.mock("../lib/api", () => {
  const actual = jest.requireActual("../lib/api");
  return { ...actual, recommendApi: jest.fn() };
});

jest.mock("../lib/useVoiceRecorder", () => {
  const actual = jest.requireActual("../lib/useVoiceRecorder");
  return { ...actual, useVoiceRecorder: jest.fn() };
});

const mockRecommendApi = recommendApi as jest.MockedFunction<typeof recommendApi>;
const mockUseRecorder = useVoiceRecorder as jest.MockedFunction<
  typeof useVoiceRecorder
>;

function makeRecorder(overrides: Partial<VoiceRecorder> = {}): VoiceRecorder {
  return {
    status: "idle",
    elapsedMs: 0,
    audioBlob: null,
    errorMessage: null,
    start: jest.fn(),
    stop: jest.fn(),
    reset: jest.fn(),
    ...overrides,
  };
}

afterEach(() => {
  jest.clearAllMocks();
});

describe("VoiceCapture", () => {
  it("idle: 녹음 시작 버튼과 안내가 보이고, 클릭 시 start 호출", () => {
    const start = jest.fn();
    mockUseRecorder.mockReturnValue(makeRecorder({ start }));

    render(<VoiceCapture />);

    const btn = screen.getByRole("button", { name: /녹음 시작/ });
    expect(btn).toBeInTheDocument();
    expect(screen.getByText(/감정을 분석/)).toBeInTheDocument();

    fireEvent.click(btn);
    expect(start).toHaveBeenCalledTimes(1);
  });

  it("recording: 녹음 중 표시·진행률·중지 버튼, 클릭 시 stop 호출", () => {
    const stop = jest.fn();
    mockUseRecorder.mockReturnValue(
      makeRecorder({ status: "recording", elapsedMs: 2300, stop })
    );

    render(<VoiceCapture />);

    expect(screen.getByText(/녹음 중…/)).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();

    const stopBtn = screen.getByRole("button", { name: /녹음 중지/ });
    fireEvent.click(stopBtn);
    expect(stop).toHaveBeenCalledTimes(1);
  });

  it("recorded: 유효 녹음이면 자동 업로드 후 추천 곡 수를 표시", async () => {
    mockRecommendApi.mockResolvedValue({
      tracks: [
        { title: "a", artist: "x", album: "z", duration_sec: 100 },
        { title: "b", artist: "y", album: "w", duration_sec: 120 },
      ],
    });
    mockUseRecorder.mockReturnValue(
      makeRecorder({ status: "recorded", audioBlob: new Blob(["x"]) })
    );

    render(<VoiceCapture />);

    await waitFor(() => expect(mockRecommendApi).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/추천 2곡/)).toBeInTheDocument();
  });

  it("업로드 실패 시 오류 메시지와 재시도 버튼 표시", async () => {
    mockRecommendApi.mockRejectedValue(new ApiError(500, "서버 오류"));
    mockUseRecorder.mockReturnValue(
      makeRecorder({ status: "recorded", audioBlob: new Blob(["x"]) })
    );

    render(<VoiceCapture />);

    expect(await screen.findByText("서버 오류")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /전송 다시 시도/ })
    ).toBeInTheDocument();
  });

  it("too_short: 최소 길이 안내와 다시 녹음 버튼", () => {
    const reset = jest.fn();
    mockUseRecorder.mockReturnValue(
      makeRecorder({ status: "too_short", reset })
    );

    render(<VoiceCapture />);

    expect(screen.getByRole("alert")).toHaveTextContent(/너무 짧/);
    const retry = screen.getByRole("button", { name: /처음부터 다시/ });
    fireEvent.click(retry);
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it("denied: 권한 거부 메시지 표시", () => {
    mockUseRecorder.mockReturnValue(
      makeRecorder({
        status: "denied",
        errorMessage: "마이크 권한이 거부되었습니다.",
      })
    );

    render(<VoiceCapture />);
    expect(screen.getByRole("alert")).toHaveTextContent(/마이크 권한이 거부/);
  });

  it("onResult 콜백으로 추천 결과를 전달", async () => {
    const onResult = jest.fn();
    const result = {
      tracks: [{ title: "a", artist: "x", album: "z", duration_sec: 100 }],
    };
    mockRecommendApi.mockResolvedValue(result);
    mockUseRecorder.mockReturnValue(
      makeRecorder({ status: "recorded", audioBlob: new Blob(["x"]) })
    );

    render(<VoiceCapture onResult={onResult} />);

    await waitFor(() => expect(onResult).toHaveBeenCalledWith(result));
  });
});
