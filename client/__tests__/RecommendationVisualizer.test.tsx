/**
 * RecommendationVisualizer 단위 테스트 (#46).
 * loading 스켈레톤/error/empty/track 리스트 렌더, formatDuration, renderRowActions 슬롯.
 */
import { render, screen } from "@testing-library/react";

import RecommendationVisualizer from "../components/RecommendationVisualizer";
import type { Track, RecommendationVisualizerProps } from "../components/RecommendationVisualizer";

/* ── CSS Modules mock ── */

jest.mock("../styles/recommend.module.css", () => new Proxy({}, { get: (_, k) => String(k) }), {
  virtual: true,
});

/* ── Fixtures ── */

function makeTrack(overrides: Partial<Track> = {}): Track {
  return {
    track_id: "t-1",
    title: "Test Song",
    artist: "Test Artist",
    album: "Test Album",
    duration_sec: 480,
    preview_url: null,
    ...overrides,
  };
}

const defaultProps: RecommendationVisualizerProps = {
  tracks: [],
  loading: false,
  error: null,
};

afterEach(() => jest.clearAllMocks());

describe("RecommendationVisualizer — loading", () => {
  it("loading=true → aria-label='추천 곡을 불러오는 중…' 컨테이너 렌더링", () => {
    render(<RecommendationVisualizer {...defaultProps} loading={true} />);

    // 컨테이너(div)와 내부 ul 모두 같은 aria-label을 가지므로 getAllByLabelText 사용
    const elements = screen.getAllByLabelText("추천 곡을 불러오는 중…");
    expect(elements.length).toBeGreaterThanOrEqual(1);
  });

  it("loading=true → aria-busy=true", () => {
    render(<RecommendationVisualizer {...defaultProps} loading={true} />);

    // aria-busy=true 인 컨테이너 div를 직접 쿼리
    const container = document.querySelector('[aria-busy="true"]');
    expect(container).toBeInTheDocument();
    expect(container).toHaveAttribute("aria-busy", "true");
  });

  it("loading=true → 스켈레톤 ul이 있다", () => {
    render(<RecommendationVisualizer {...defaultProps} loading={true} />);

    // 내부 스켈레톤 ul
    const skeletonUl = document.querySelector('ul[aria-label="추천 곡을 불러오는 중…"]');
    expect(skeletonUl).toBeInTheDocument();
  });

  it("loading=true → 에러 메시지가 없다", () => {
    render(<RecommendationVisualizer {...defaultProps} loading={true} error="오류" />);

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("loading=true → 트랙 목록이 없다", () => {
    const tracks = [makeTrack({ title: "Song A" })];
    render(<RecommendationVisualizer tracks={tracks} loading={true} />);

    expect(screen.queryByText("Song A")).not.toBeInTheDocument();
  });
});

describe("RecommendationVisualizer — error", () => {
  it("error 문자열 → role='alert' 렌더링", () => {
    render(<RecommendationVisualizer {...defaultProps} error="서버 오류가 발생했습니다." />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("error 메시지 텍스트가 표시된다", () => {
    render(<RecommendationVisualizer {...defaultProps} error="네트워크 오류" />);

    expect(screen.getByText("네트워크 오류")).toBeInTheDocument();
  });

  it("error → 트랙 목록이 없다", () => {
    const tracks = [makeTrack({ title: "Song A" })];
    render(<RecommendationVisualizer tracks={tracks} loading={false} error="오류" />);

    expect(screen.queryByRole("list", { name: "추천 곡 목록" })).not.toBeInTheDocument();
  });

  it("error → loading 스켈레톤이 없다 (loading=false 우선)", () => {
    render(<RecommendationVisualizer {...defaultProps} loading={false} error="오류" />);

    expect(screen.queryByLabelText("추천 곡을 불러오는 중…")).not.toBeInTheDocument();
  });
});

describe("RecommendationVisualizer — empty", () => {
  it("tracks=[] + loading=false + error=null → 빈 상태 메시지 표시", () => {
    render(<RecommendationVisualizer tracks={[]} loading={false} error={null} />);

    expect(screen.getByText("추천 결과가 없습니다.")).toBeInTheDocument();
  });

  it("빈 상태 서브타이틀 표시", () => {
    render(<RecommendationVisualizer tracks={[]} loading={false} />);

    expect(
      screen.getByText("감정을 입력하면 어울리는 곡을 추천해 드립니다.")
    ).toBeInTheDocument();
  });

  it("빈 상태 → 트랙 목록이 없다", () => {
    render(<RecommendationVisualizer tracks={[]} loading={false} />);

    expect(screen.queryByRole("list", { name: "추천 곡 목록" })).not.toBeInTheDocument();
  });
});

describe("RecommendationVisualizer — track list", () => {
  const tracks: Track[] = [
    makeTrack({ track_id: "t-1", title: "Song 1", artist: "Artist 1", album: "Album 1", duration_sec: 480 }),
    makeTrack({ track_id: "t-2", title: "Song 2", artist: "Artist 2", album: "Album 2", duration_sec: 75 }),
    makeTrack({ track_id: "t-3", title: "Song 3", artist: "Artist 3", album: "Album 3", duration_sec: 0 }),
  ];

  it("role='list' + aria-label='추천 곡 목록' 렌더링", () => {
    render(<RecommendationVisualizer tracks={tracks} loading={false} />);

    expect(screen.getByRole("list", { name: "추천 곡 목록" })).toBeInTheDocument();
  });

  it("트랙 수만큼 listitem 렌더링", () => {
    render(<RecommendationVisualizer tracks={tracks} loading={false} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("각 트랙 제목이 표시된다", () => {
    render(<RecommendationVisualizer tracks={tracks} loading={false} />);

    expect(screen.getByText("Song 1")).toBeInTheDocument();
    expect(screen.getByText("Song 2")).toBeInTheDocument();
    expect(screen.getByText("Song 3")).toBeInTheDocument();
  });

  it("각 트랙 아티스트가 표시된다", () => {
    render(<RecommendationVisualizer tracks={tracks} loading={false} />);

    expect(screen.getByText("Artist 1")).toBeInTheDocument();
    expect(screen.getByText("Artist 2")).toBeInTheDocument();
  });

  it("각 트랙 앨범이 표시된다", () => {
    render(<RecommendationVisualizer tracks={tracks} loading={false} />);

    expect(screen.getByText("Album 1")).toBeInTheDocument();
  });

  describe("formatDuration", () => {
    it("480초 → '8:00'", () => {
      render(<RecommendationVisualizer tracks={[makeTrack({ duration_sec: 480 })]} loading={false} />);
      expect(screen.getByText("8:00")).toBeInTheDocument();
    });

    it("75초 → '1:15'", () => {
      render(<RecommendationVisualizer tracks={[makeTrack({ duration_sec: 75 })]} loading={false} />);
      expect(screen.getByText("1:15")).toBeInTheDocument();
    });

    it("0초 → '0:00'", () => {
      render(<RecommendationVisualizer tracks={[makeTrack({ duration_sec: 0 })]} loading={false} />);
      expect(screen.getByText("0:00")).toBeInTheDocument();
    });

    it("재생 시간 aria-label 포함 (480초)", () => {
      render(<RecommendationVisualizer tracks={[makeTrack({ duration_sec: 480 })]} loading={false} />);
      expect(screen.getByLabelText("재생 시간 8:00")).toBeInTheDocument();
    });

    it("재생 시간 aria-label 포함 (75초)", () => {
      render(<RecommendationVisualizer tracks={[makeTrack({ duration_sec: 75 })]} loading={false} />);
      expect(screen.getByLabelText("재생 시간 1:15")).toBeInTheDocument();
    });
  });

  describe("renderRowActions 슬롯", () => {
    it("renderRowActions 미제공 → 액션 영역 없음", () => {
      render(<RecommendationVisualizer tracks={tracks} loading={false} />);

      expect(screen.queryByTestId("row-action")).not.toBeInTheDocument();
    });

    it("renderRowActions 제공 → 트랙마다 한 번씩 호출된다", () => {
      const renderRowActions = jest.fn((track: Track) => (
        <button data-testid="row-action">{track.title}</button>
      ));

      render(
        <RecommendationVisualizer tracks={tracks} loading={false} renderRowActions={renderRowActions} />
      );

      expect(renderRowActions).toHaveBeenCalledTimes(3);
    });

    it("renderRowActions 제공 → 각 트랙 객체가 인자로 전달된다", () => {
      const renderRowActions = jest.fn(() => null);

      render(
        <RecommendationVisualizer tracks={tracks} loading={false} renderRowActions={renderRowActions} />
      );

      expect(renderRowActions).toHaveBeenNthCalledWith(1, tracks[0]);
      expect(renderRowActions).toHaveBeenNthCalledWith(2, tracks[1]);
      expect(renderRowActions).toHaveBeenNthCalledWith(3, tracks[2]);
    });

    it("renderRowActions 반환값이 DOM에 렌더링된다", () => {
      const renderRowActions = (track: Track) => (
        <button data-testid={`action-${track.track_id}`}>액션</button>
      );

      render(
        <RecommendationVisualizer tracks={tracks} loading={false} renderRowActions={renderRowActions} />
      );

      expect(screen.getByTestId("action-t-1")).toBeInTheDocument();
      expect(screen.getByTestId("action-t-2")).toBeInTheDocument();
      expect(screen.getByTestId("action-t-3")).toBeInTheDocument();
    });
  });
});

describe("RecommendationVisualizer — ArtPlaceholder", () => {
  it("트랙 목록 렌더 시 앨범아트 placeholder(aria-hidden) 가 존재한다", () => {
    const track = makeTrack();
    render(<RecommendationVisualizer tracks={[track]} loading={false} />);

    // aria-hidden=true 인 div 가 있어야 함
    const placeholders = document.querySelectorAll('[aria-hidden="true"]');
    expect(placeholders.length).toBeGreaterThan(0);
  });
});
