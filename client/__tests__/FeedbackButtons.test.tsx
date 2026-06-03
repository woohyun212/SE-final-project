/**
 * FeedbackButtons 단위 테스트 (#47).
 * 낙관적 업데이트(즉시 onChange) + feedbackApi 호출 + 실패 롤백 + disabled 검증.
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

import FeedbackButtons from "../components/FeedbackButtons";
import { feedbackApi } from "../lib/api";

jest.mock("../lib/api", () => ({ feedbackApi: jest.fn() }));
const mockFeedback = feedbackApi as jest.Mock;

afterEach(() => jest.clearAllMocks());

describe("FeedbackButtons", () => {
  it("좋아요 클릭 → onChange('like') 즉시 + feedbackApi('like', trackId, recId)", async () => {
    mockFeedback.mockResolvedValue(undefined);
    const onChange = jest.fn();

    render(
      <FeedbackButtons trackId="t-1" recommendationId="s-1" onChange={onChange} />
    );
    fireEvent.click(screen.getByRole("button", { name: "좋아요" }));

    // 낙관적 — 즉시 호출
    expect(onChange).toHaveBeenCalledWith("like");
    await waitFor(() =>
      expect(mockFeedback).toHaveBeenCalledWith("like", "t-1", "s-1")
    );
  });

  it("recommendationId 없으면 버튼 disabled (세션 없음)", () => {
    render(<FeedbackButtons trackId="t-1" />);
    expect(screen.getByRole("button", { name: "좋아요" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "싫어요" })).toBeDisabled();
  });

  it("API 실패 시 이전 값으로 롤백", async () => {
    mockFeedback.mockRejectedValue(new Error("network"));
    const onChange = jest.fn();

    render(
      <FeedbackButtons
        trackId="t-1"
        recommendationId="s-1"
        value="dislike"
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "좋아요" }));

    expect(onChange).toHaveBeenCalledWith("like"); // 낙관적
    await waitFor(() =>
      expect(onChange).toHaveBeenLastCalledWith("dislike")
    ); // 롤백
  });
});
