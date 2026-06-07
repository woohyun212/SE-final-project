/**
 * EmotionMusicChartRender.test.tsx — EmotionMusicChart 컴포넌트 렌더 커버리지 (#45)
 *
 * 목적: 렌더 경로(SVG 축·격자·범례·툴팁·각 곡 점·로딩·에러)를 실행해
 * EmotionMusicChart.tsx 라인 커버리지를 끌어올린다.
 * (좌표 변환 단위 테스트는 emotionChart.test.ts 에서 커버됨)
 */
import { render, screen, fireEvent } from '@testing-library/react';
import EmotionMusicChart from '../components/EmotionMusicChart';
import type { RecommendedTrack, EmotionPoint } from '../lib/recommend';

/* ── 샘플 데이터: valence/energy 4사분면 분포 6곡 ── */
const TRACKS: RecommendedTrack[] = [
  // 1사분면: 긍정·활발 (신남)
  {
    track_id: 'q1-a',
    title: '신나는 곡 A',
    artist: 'Artist A',
    album: 'Album A',
    duration_sec: 200,
    valence: 0.8,
    energy: 0.9,
  },
  {
    track_id: 'q1-b',
    title: '신나는 곡 B',
    artist: 'Artist B',
    album: 'Album B',
    duration_sec: 180,
    valence: 0.9,
    energy: 0.7,
    preview_url: 'https://cdn.example/b.mp3',
  },
  // 2사분면: 부정·활발 (긴장)
  {
    track_id: 'q2-a',
    title: '긴장 곡 A',
    artist: 'Artist C',
    album: 'Album C',
    duration_sec: 220,
    valence: 0.2,
    energy: 0.8,
  },
  // 3사분면: 부정·차분 (우울)
  {
    track_id: 'q3-a',
    title: '우울 곡 A',
    artist: 'Artist D',
    album: 'Album D',
    duration_sec: 240,
    valence: 0.15,
    energy: 0.2,
    preview_url: null,
  },
  // 4사분면: 긍정·차분 (평온)
  {
    track_id: 'q4-a',
    title: '평온 곡 A',
    artist: 'Artist E',
    album: 'Album E',
    duration_sec: 210,
    valence: 0.75,
    energy: 0.25,
  },
  // 중앙부
  {
    track_id: 'center',
    title: '중앙 곡',
    artist: 'Artist F',
    album: 'Album F',
    duration_sec: 190,
    valence: 0.5,
    energy: 0.5,
    reason: '감정과 에너지가 균형 잡힌 곡입니다.',
  },
];

const USER_EMOTION: EmotionPoint = {
  valence: 0.6,
  energy: 0.65,
  label: '현재 감정',
};

/* ── 헬퍼: 기본 props 로 렌더 ── */
function renderChart(overrides?: Partial<Parameters<typeof EmotionMusicChart>[0]>) {
  return render(
    <EmotionMusicChart
      tracks={TRACKS}
      userEmotion={USER_EMOTION}
      {...overrides}
    />,
  );
}

/* ────────────────────────────────────────────────────────
   1. 정상 렌더 경로
   ──────────────────────────────────────────────────────── */
describe('EmotionMusicChart — 정상 렌더', () => {
  it('SVG 차트 래퍼가 role=img 로 렌더된다', () => {
    renderChart();
    const chartArea = screen.getByRole('img', { name: /감정-음악 2D 산점도/ });
    expect(chartArea).toBeInTheDocument();
  });

  it('aria-label 에 현재 감정 valence/energy 값이 포함된다', () => {
    renderChart();
    const el = screen.getByRole('img', { name: /valence 0\.60/ });
    expect(el).toBeInTheDocument();
  });

  it('aria-label 에 추천 곡 수가 포함된다', () => {
    renderChart();
    const el = screen.getByRole('img', { name: /추천 곡 6개/ });
    expect(el).toBeInTheDocument();
  });

  it('사용자 감정 별 마커(aria-label)가 렌더된다', () => {
    const { container } = renderChart();
    // SVG는 aria-hidden이므로 querySelector로 직접 접근
    const star = container.querySelector('polygon[aria-label]');
    expect(star).not.toBeNull();
    expect(star!.getAttribute('aria-label')).toMatch(/현재 감정: valence 0\.60 · energy 0\.65/);
  });

  it('각 트랙 마커(aria-label)가 렌더된다', () => {
    const { container } = renderChart();
    // TrackMarker의 circle들은 role=img aria-label 보유 (SVG 내부 aria-hidden 하위)
    const circles = container.querySelectorAll('circle[aria-label]');
    // 트랙 수만큼 circle이 있어야 함 (active ring 제외, role=img circle만)
    const trackCircles = Array.from(circles).filter((el) =>
      el.getAttribute('role') === 'img',
    );
    expect(trackCircles.length).toBe(TRACKS.length);
  });

  it('범례에 "현재 감정 (★)" 텍스트가 있다', () => {
    renderChart();
    expect(screen.getByText('현재 감정 (★)')).toBeInTheDocument();
  });

  it('범례에 "추천 곡 (●)" 텍스트가 있다', () => {
    renderChart();
    expect(screen.getByText('추천 곡 (●)')).toBeInTheDocument();
  });

  it('X축 라벨 텍스트가 렌더된다', () => {
    renderChart();
    expect(screen.getByText('부정 ← 감정가 → 긍정')).toBeInTheDocument();
  });

  it('Y축 라벨 텍스트가 렌더된다', () => {
    renderChart();
    expect(screen.getByText('차분 ← 활기 → 활발')).toBeInTheDocument();
  });

  it('사분면 라벨(신남·긴장·평온·우울)이 모두 렌더된다', () => {
    renderChart();
    ['신남', '긴장', '평온', '우울'].forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });
});

/* ────────────────────────────────────────────────────────
   2. 로딩 상태
   ──────────────────────────────────────────────────────── */
describe('EmotionMusicChart — 로딩 상태', () => {
  it('loading=true 이면 aria-busy 스켈레톤이 렌더된다', () => {
    renderChart({ loading: true });
    const skeleton = screen.getByLabelText('차트를 불러오는 중…');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute('aria-busy', 'true');
  });

  it('loading=true 이면 차트 SVG 영역이 없다', () => {
    renderChart({ loading: true });
    expect(screen.queryByRole('img', { name: /감정-음악 2D 산점도/ })).toBeNull();
  });
});

/* ────────────────────────────────────────────────────────
   3. 에러 상태
   ──────────────────────────────────────────────────────── */
describe('EmotionMusicChart — 에러 상태', () => {
  it('error 문자열이 있으면 role=alert 가 렌더된다', () => {
    renderChart({ error: '데이터를 불러올 수 없습니다.' });
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent('데이터를 불러올 수 없습니다.');
  });

  it('에러 상태에서는 차트 SVG 가 없다', () => {
    renderChart({ error: '오류' });
    expect(screen.queryByRole('img', { name: /감정-음악 2D 산점도/ })).toBeNull();
  });
});

/* ────────────────────────────────────────────────────────
   4. 툴팁 hover 상호작용
   ──────────────────────────────────────────────────────── */
/* 트랙 circle 마커를 인덱스로 찾는 헬퍼 */
function getTrackCircle(container: HTMLElement, index: number): Element {
  const circles = container.querySelectorAll('circle[role="img"]');
  return circles[index];
}

describe('EmotionMusicChart — 툴팁 hover', () => {
  it('트랙 마커에 mouseEnter 하면 툴팁이 나타난다', () => {
    const { container } = renderChart();
    const firstTrack = TRACKS[0];
    const marker = getTrackCircle(container, 0);

    fireEvent.mouseEnter(marker);

    // 툴팁 div 안의 텍스트 확인
    expect(screen.getByText(firstTrack.title)).toBeInTheDocument();
    expect(screen.getByText(firstTrack.artist)).toBeInTheDocument();
  });

  it('mouseLeave 하면 툴팁이 사라진다', () => {
    const { container } = renderChart();
    const firstTrack = TRACKS[0];
    const marker = getTrackCircle(container, 0);

    fireEvent.mouseEnter(marker);
    // 툴팁 title p 태그가 존재함
    expect(screen.getByText(firstTrack.title)).toBeInTheDocument();

    fireEvent.mouseLeave(marker);
    // 툴팁이 사라지면 p.tooltipArtist 도 사라짐 (텍스트 노드로 렌더된 것만)
    const artistNodes = screen.queryAllByText(firstTrack.artist);
    const tooltipArtistNodes = artistNodes.filter(
      (el) => el.tagName === 'P',
    );
    expect(tooltipArtistNodes).toHaveLength(0);
  });

  it('두 번째 트랙에 mouseEnter 하면 해당 툴팁이 나타난다', () => {
    const { container } = renderChart();
    const track = TRACKS[1];
    const marker = getTrackCircle(container, 1);

    fireEvent.mouseEnter(marker);
    expect(screen.getByText(track.artist)).toBeInTheDocument();
  });

  it('focus/blur 로도 툴팁 활성/비활성 된다', () => {
    const { container } = renderChart();
    const track = TRACKS[2];
    const marker = getTrackCircle(container, 2);

    fireEvent.focus(marker);
    expect(screen.getByText(track.artist)).toBeInTheDocument();

    fireEvent.blur(marker);
    const artistNodes = screen.queryAllByText(track.artist);
    const tooltipArtistNodes = artistNodes.filter((el) => el.tagName === 'P');
    expect(tooltipArtistNodes).toHaveLength(0);
  });

  it('active 상태에서 Escape 키 누르면 툴팁 닫힘', () => {
    const { container } = renderChart();
    const track = TRACKS[3];
    const marker = getTrackCircle(container, 3);

    fireEvent.mouseEnter(marker);
    expect(screen.getByText(track.artist)).toBeInTheDocument();

    fireEvent.keyDown(marker, { key: 'Escape' });
    const artistNodes = screen.queryAllByText(track.artist);
    const tooltipArtistNodes = artistNodes.filter((el) => el.tagName === 'P');
    expect(tooltipArtistNodes).toHaveLength(0);
  });
});

/* ────────────────────────────────────────────────────────
   5. 빈 트랙 목록
   ──────────────────────────────────────────────────────── */
describe('EmotionMusicChart — 빈 트랙 목록', () => {
  it('tracks=[] 이어도 차트가 렌더된다', () => {
    renderChart({ tracks: [] });
    const chartArea = screen.getByRole('img', { name: /감정-음악 2D 산점도/ });
    expect(chartArea).toBeInTheDocument();
  });

  it('tracks=[] 이면 추천 곡 0개 aria-label', () => {
    renderChart({ tracks: [] });
    expect(screen.getByRole('img', { name: /추천 곡 0개/ })).toBeInTheDocument();
  });
});

/* ────────────────────────────────────────────────────────
   6. userEmotion label 없는 경우 (기본값 '현재 감정')
   ──────────────────────────────────────────────────────── */
describe('EmotionMusicChart — userEmotion label 미제공', () => {
  it('label 없는 EmotionPoint 도 정상 렌더', () => {
    const { container } = renderChart({
      userEmotion: { valence: 0.3, energy: 0.7 },
    });
    // label 이 undefined 이면 기본값 '현재 감정' 사용
    // SVG는 aria-hidden이므로 querySelector로 polygon aria-label 확인
    const star = container.querySelector('polygon[aria-label]');
    expect(star).not.toBeNull();
    expect(star!.getAttribute('aria-label')).toMatch(/현재 감정: valence 0\.30 · energy 0\.70/);
  });
});

/* ────────────────────────────────────────────────────────
   7. 툴팁 위치 분기 (xFrac > 0.65 / yFrac > 0.65)
   ──────────────────────────────────────────────────────── */
describe('EmotionMusicChart — 툴팁 위치 flip 분기', () => {
  it('우측 하단 트랙(valence 높고 energy 낮음) hover 시 툴팁 렌더', () => {
    // valence=0.95 → xFrac > 0.65, energy=0.05 → yFrac > 0.65 → flipX+flipY 분기
    const tracks: RecommendedTrack[] = [
      {
        track_id: 'flip-test',
        title: 'Flip 곡',
        artist: 'Flip Artist',
        album: 'Flip Album',
        duration_sec: 200,
        valence: 0.95,
        energy: 0.05,
      },
    ];
    const { container } = render(
      <EmotionMusicChart
        tracks={tracks}
        userEmotion={{ valence: 0.5, energy: 0.5 }}
      />,
    );
    const marker = getTrackCircle(container, 0);
    fireEvent.mouseEnter(marker);
    expect(screen.getByText('Flip Artist')).toBeInTheDocument();
  });

  it('좌측 상단 트랙(valence 낮고 energy 높음) hover 시 툴팁 렌더', () => {
    // valence=0.1 → xFrac < 0.65, energy=0.9 → yFrac < 0.65 → flipX=false, flipY=false
    const tracks: RecommendedTrack[] = [
      {
        track_id: 'flip-tl',
        title: '좌상단 곡',
        artist: '좌상단 Artist',
        album: 'TL Album',
        duration_sec: 200,
        valence: 0.1,
        energy: 0.9,
      },
    ];
    const { container } = render(
      <EmotionMusicChart
        tracks={tracks}
        userEmotion={{ valence: 0.5, energy: 0.5 }}
      />,
    );
    const marker = getTrackCircle(container, 0);
    fireEvent.mouseEnter(marker);
    expect(screen.getByText('좌상단 Artist')).toBeInTheDocument();
  });

  it('우측 상단 트랙(valence 높고 energy 높음) hover 시 툴팁 렌더 — flipX only', () => {
    // valence=0.9 → xFrac > 0.65, energy=0.9 → yFrac < 0.65
    const tracks: RecommendedTrack[] = [
      {
        track_id: 'flip-tr',
        title: '우상단 곡',
        artist: '우상단 Artist',
        album: 'TR Album',
        duration_sec: 200,
        valence: 0.9,
        energy: 0.9,
      },
    ];
    const { container } = render(
      <EmotionMusicChart
        tracks={tracks}
        userEmotion={{ valence: 0.5, energy: 0.5 }}
      />,
    );
    const marker = getTrackCircle(container, 0);
    fireEvent.mouseEnter(marker);
    expect(screen.getByText('우상단 Artist')).toBeInTheDocument();
  });
});
