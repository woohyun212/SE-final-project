/**
 * RecommendationReasonCard 단위 테스트 (#46).
 * reason 있을 때 텍스트 표시, 없을 때 skeleton, RecommendationReasonList 래퍼.
 */
import { render, screen } from "@testing-library/react";

import RecommendationReasonCard, {
  RecommendationReasonList,
} from "../components/RecommendationReasonCard";
import type { RecommendationReasonCardProps } from "../components/RecommendationReasonCard";
import type { RecommendedTrack } from "../lib/recommend";

/* ── Fixtures ── */

function makeTrack(overrides: Partial<RecommendedTrack> = {}): RecommendedTrack {
  return {
    track_id: "t-1",
    title: "Test Song",
    artist: "Test Artist",
    album: "Test Album",
    duration_sec: 213,
    valence: 0.7,
    energy: 0.6,
    reason: null,
    ...overrides,
  };
}

/* ── CSS Modules mock (next/jest transforms handle this, but guard for safety) ── */

jest.mock("../styles/reasonCard.module.css", () => new Proxy({}, { get: (_, k) => String(k) }), {
  virtual: true,
});

afterEach(() => jest.clearAllMocks());

describe("RecommendationReasonCard", () => {
  it("트랙 제목·아티스트·앨범을 렌더링한다", () => {
    const track = makeTrack({ title: "Song A", artist: "Artist B", album: "Album C" });
    render(<RecommendationReasonCard track={track} />);

    expect(screen.getByText("Song A")).toBeInTheDocument();
    expect(screen.getByText("Artist B")).toBeInTheDocument();
    expect(screen.getByText("Album C")).toBeInTheDocument();
  });

  it("duration_sec 을 m:ss 포맷으로 표시한다 (213초 → '3:33')", () => {
    const track = makeTrack({ duration_sec: 213 });
    render(<RecommendationReasonCard track={track} />);

    expect(screen.getByText("3:33")).toBeInTheDocument();
  });

  it("duration_sec 을 m:ss 포맷으로 표시한다 (247초 → '4:07')", () => {
    const track = makeTrack({ duration_sec: 247 });
    render(<RecommendationReasonCard track={track} />);

    expect(screen.getByText("4:07")).toBeInTheDocument();
  });

  it("재생 시간 aria-label 을 포함한다", () => {
    const track = makeTrack({ duration_sec: 213 });
    render(<RecommendationReasonCard track={track} />);

    expect(screen.getByLabelText("재생 시간 3:33")).toBeInTheDocument();
  });

  it("article 의 aria-label 이 '제목 — 아티스트' 형식이다", () => {
    const track = makeTrack({ title: "My Song", artist: "My Artist" });
    render(<RecommendationReasonCard track={track} />);

    expect(screen.getByRole("article", { name: "My Song — My Artist" })).toBeInTheDocument();
  });

  describe("reason 이 존재할 때", () => {
    it("추천 이유 텍스트를 blockquote 안에 표시한다", () => {
      const track = makeTrack({ reason: "이 곡은 당신의 감정에 잘 어울립니다." });
      render(<RecommendationReasonCard track={track} />);

      expect(screen.getByText("이 곡은 당신의 감정에 잘 어울립니다.")).toBeInTheDocument();
      // blockquote 요소가 존재해야 한다
      expect(document.querySelector("blockquote")).toBeInTheDocument();
    });

    it("blockquote 의 aria-label 이 '추천 이유'이다", () => {
      const track = makeTrack({ reason: "좋은 이유" });
      render(<RecommendationReasonCard track={track} />);

      expect(screen.getByRole("blockquote", { name: "추천 이유" })).toBeInTheDocument();
    });

    it("skeleton 이 렌더링되지 않는다", () => {
      const track = makeTrack({ reason: "Some reason" });
      render(<RecommendationReasonCard track={track} />);

      expect(screen.queryByLabelText("추천 이유 생성 중…")).not.toBeInTheDocument();
    });
  });

  describe("reason 이 null/undefined/빈 문자열일 때", () => {
    it("reason=null → skeleton을 렌더링한다", () => {
      const track = makeTrack({ reason: null });
      render(<RecommendationReasonCard track={track} />);

      expect(screen.getByLabelText("추천 이유 생성 중…")).toBeInTheDocument();
    });

    it("reason=undefined → skeleton을 렌더링한다", () => {
      const track = makeTrack({ reason: undefined });
      render(<RecommendationReasonCard track={track} />);

      expect(screen.getByLabelText("추천 이유 생성 중…")).toBeInTheDocument();
    });

    it("reason='' (빈 문자열) → skeleton을 렌더링한다", () => {
      const track = makeTrack({ reason: "" });
      render(<RecommendationReasonCard track={track} />);

      expect(screen.getByLabelText("추천 이유 생성 중…")).toBeInTheDocument();
    });

    it("reason=null → skeleton 이 aria-busy=true 이다", () => {
      const track = makeTrack({ reason: null });
      render(<RecommendationReasonCard track={track} />);

      const skeleton = screen.getByLabelText("추천 이유 생성 중…");
      expect(skeleton).toHaveAttribute("aria-busy", "true");
    });

    it("reason=null → blockquote 가 렌더링되지 않는다", () => {
      const track = makeTrack({ reason: null });
      render(<RecommendationReasonCard track={track} />);

      expect(document.querySelector("blockquote")).not.toBeInTheDocument();
    });
  });
});

describe("RecommendationReasonList", () => {
  const tracks: RecommendedTrack[] = [
    makeTrack({ track_id: "t-1", title: "Song 1", artist: "Artist 1", reason: "이유 1" }),
    makeTrack({ track_id: "t-2", title: "Song 2", artist: "Artist 2", reason: null }),
    makeTrack({ track_id: "t-3", title: "Song 3", artist: "Artist 3", reason: "이유 3" }),
  ];

  it("role='list' + aria-label='추천 곡 및 이유 목록' ul을 렌더링한다", () => {
    render(<RecommendationReasonList tracks={tracks} />);

    expect(screen.getByRole("list", { name: "추천 곡 및 이유 목록" })).toBeInTheDocument();
  });

  it("tracks 개수만큼 카드를 렌더링한다", () => {
    render(<RecommendationReasonList tracks={tracks} />);

    expect(screen.getAllByRole("article")).toHaveLength(3);
  });

  it("각 트랙 제목이 모두 표시된다", () => {
    render(<RecommendationReasonList tracks={tracks} />);

    expect(screen.getByText("Song 1")).toBeInTheDocument();
    expect(screen.getByText("Song 2")).toBeInTheDocument();
    expect(screen.getByText("Song 3")).toBeInTheDocument();
  });

  it("reason 있는 카드는 텍스트, 없는 카드는 skeleton을 렌더링한다", () => {
    render(<RecommendationReasonList tracks={tracks} />);

    expect(screen.getByText("이유 1")).toBeInTheDocument();
    expect(screen.getByText("이유 3")).toBeInTheDocument();
    // t-2 는 reason=null → skeleton
    expect(screen.getByLabelText("추천 이유 생성 중…")).toBeInTheDocument();
  });

  it("빈 배열이면 li 가 없다", () => {
    render(<RecommendationReasonList tracks={[]} />);

    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });
});
