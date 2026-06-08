/**
 * HistoryList 단위 테스트 (#50, US-20).
 * props-only 컴포넌트. loading/error/empty/items 렌더 + 아코디언 토글 검증.
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import HistoryList from '../components/HistoryList';
import type { HistoryItem } from '../lib/recommend';

// CSS 모듈은 Next.js jest 설정이 자동으로 identity-obj-proxy 로 처리.

// ── 픽스처 ──────────────────────────────────────────────────────────────────

function makeItem(overrides: Partial<HistoryItem> = {}): HistoryItem {
  return {
    id: 'sess-1',
    user_valence: 0.7,
    user_energy: 0.4,
    created_at: '2026-06-03T14:30:00Z',
    recommended_tracks: [
      { track_id: 't-2', title: 'Beta', artist: 'BandB', rank: 2, score: 0.8 },
      { track_id: 't-1', title: 'Alpha', artist: 'BandA', rank: 1, score: 0.9 },
    ],
    feedbacks: [
      { track_id: 't-1', title: 'Alpha', artist: 'BandA', feedback_type: 'like' },
    ],
    ...overrides,
  };
}

// ── 테스트 ───────────────────────────────────────────────────────────────────

describe('HistoryList', () => {
  // 1. loading 상태
  it('loading=true 이면 스켈레톤 목록(aria-busy)이 렌더된다', () => {
    render(<HistoryList items={[]} loading={true} />);
    const skeleton = screen.getByRole('list', { name: '이력 불러오는 중' });
    expect(skeleton).toHaveAttribute('aria-busy', 'true');
    // 스켈레톤 카드 3개
    expect(skeleton.children).toHaveLength(3);
  });

  // 2. error 상태
  it('error prop 이 있으면 role=alert 로 에러 메시지가 렌더된다', () => {
    render(<HistoryList items={[]} error="네트워크 오류" />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('네트워크 오류');
  });

  it('error 와 loading 이 모두 없으면 alert 가 없다', () => {
    render(<HistoryList items={[makeItem()]} />);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  // 3. empty 상태
  it('items=[] 이면 빈 상태 안내(role=status)가 렌더된다', () => {
    render(<HistoryList items={[]} />);
    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('추천 이력이 없습니다.');
  });

  // 4. items 렌더 — 세션 메타
  it('items 가 있으면 추천 이력 목록(aria-label)이 렌더된다', () => {
    render(<HistoryList items={[makeItem()]} />);
    expect(
      screen.getByRole('list', { name: '추천 이력 목록' }),
    ).toBeInTheDocument();
  });

  it('세션 요약에 추천 곡 수와 피드백 수가 표시된다', () => {
    render(<HistoryList items={[makeItem()]} />);
    // "추천 2곡 · 피드백 1"
    expect(screen.getByText(/추천 2곡/)).toBeInTheDocument();
    expect(screen.getByText(/피드백 1/)).toBeInTheDocument();
  });

  it('피드백이 없으면 "피드백" 문구가 없다', () => {
    const item = makeItem({ feedbacks: [] });
    render(<HistoryList items={[item]} />);
    expect(screen.queryByText(/피드백/)).toBeNull();
  });

  // 5. 감정 좌표 pill
  it('감정 좌표 pill 에 valence·energy 퍼센트가 표시된다', () => {
    render(<HistoryList items={[makeItem()]} />);
    // user_valence=0.7 → 70%, user_energy=0.4 → 40%
    const pill = screen.getByLabelText(/감정 좌표/);
    expect(pill).toHaveTextContent('V 70%');
    expect(pill).toHaveTextContent('E 40%');
  });

  // 6. 아코디언 펼침 토글 — aria-expanded
  it('초기 상태에서 버튼 aria-expanded=false', () => {
    render(<HistoryList items={[makeItem()]} />);
    const btn = screen.getByRole('button', { expanded: false });
    expect(btn).toHaveAttribute('aria-expanded', 'false');
  });

  it('버튼 클릭 시 aria-expanded=true 로 바뀌고 상세 패널이 나타난다', async () => {
    const user = userEvent.setup();
    render(<HistoryList items={[makeItem()]} />);

    const btn = screen.getByRole('button', { expanded: false });
    await user.click(btn);

    expect(btn).toHaveAttribute('aria-expanded', 'true');
    expect(
      screen.getByRole('region', { name: '이 세션의 추천 곡' }),
    ).toBeInTheDocument();
  });

  it('두 번 클릭하면 aria-expanded=false 로 복귀하고 상세 패널이 사라진다', async () => {
    const user = userEvent.setup();
    render(<HistoryList items={[makeItem()]} />);

    const btn = screen.getByRole('button', { expanded: false });
    await user.click(btn);
    await user.click(btn);

    expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(
      screen.queryByRole('region', { name: '이 세션의 추천 곡' }),
    ).toBeNull();
  });

  // 7. 상세 패널 — 추천 곡 rank 순 렌더
  it('상세 패널에서 추천 곡이 rank 오름차순으로 렌더된다', async () => {
    const user = userEvent.setup();
    render(<HistoryList items={[makeItem()]} />);

    await user.click(screen.getByRole('button', { expanded: false }));

    const list = screen.getByRole('list', { name: '추천 곡 목록' });
    const items = list.querySelectorAll('li');
    // rank 1 → Alpha, rank 2 → Beta
    expect(items[0]).toHaveTextContent('Alpha');
    expect(items[1]).toHaveTextContent('Beta');
  });

  it('상세 패널에서 아티스트 이름이 렌더된다', async () => {
    const user = userEvent.setup();
    render(<HistoryList items={[makeItem()]} />);

    await user.click(screen.getByRole('button', { expanded: false }));

    expect(screen.getByText('BandA')).toBeInTheDocument();
    expect(screen.getByText('BandB')).toBeInTheDocument();
  });

  // 8. 피드백 배지 매핑
  it('like 피드백이 있는 곡에 "좋아요" 배지가 렌더된다', async () => {
    const user = userEvent.setup();
    render(<HistoryList items={[makeItem()]} />);

    await user.click(screen.getByRole('button', { expanded: false }));

    // t-1(Alpha)에 like → aria-label="피드백: 좋아요"
    expect(screen.getByLabelText('피드백: 좋아요')).toBeInTheDocument();
  });

  it('dislike 피드백이 있는 곡에 "싫어요" 배지가 렌더된다', async () => {
    const user = userEvent.setup();
    const item = makeItem({
      feedbacks: [
        { track_id: 't-2', title: 'Beta', artist: 'BandB', feedback_type: 'dislike' },
      ],
    });
    render(<HistoryList items={[item]} />);

    await user.click(screen.getByRole('button', { expanded: false }));

    expect(screen.getByLabelText('피드백: 싫어요')).toBeInTheDocument();
  });

  it('피드백 없는 곡에는 배지가 렌더되지 않는다', async () => {
    const user = userEvent.setup();
    render(<HistoryList items={[makeItem()]} />);

    await user.click(screen.getByRole('button', { expanded: false }));

    // t-2(Beta)에는 피드백 없음 → 배지 1개만 존재
    const badges = screen.getAllByLabelText(/^피드백:/);
    expect(badges).toHaveLength(1);
  });

  // 9. recommended_tracks 빈 경우
  it('추천 곡이 없으면 "추천 곡이 없습니다" 메시지가 표시된다', async () => {
    const user = userEvent.setup();
    const item = makeItem({ recommended_tracks: [], feedbacks: [] });
    render(<HistoryList items={[item]} />);

    await user.click(screen.getByRole('button', { expanded: false }));

    expect(screen.getByText('추천 곡이 없습니다.')).toBeInTheDocument();
  });

  // 10. 여러 items 렌더
  it('items 가 여러 개면 각각 버튼이 렌더된다', () => {
    const items = [
      makeItem({ id: 'sess-1' }),
      makeItem({ id: 'sess-2', created_at: '2026-06-04T10:00:00Z' }),
    ];
    render(<HistoryList items={items} />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);
  });

  // 11. unknown feedback_type — 배지 라벨이 type 그대로
  it('알 수 없는 feedback_type 은 배지 라벨을 그대로 표시한다', async () => {
    const user = userEvent.setup();
    const item = makeItem({
      feedbacks: [
        { track_id: 't-1', title: 'Alpha', artist: 'BandA', feedback_type: 'skip' },
      ],
    });
    render(<HistoryList items={[item]} />);

    await user.click(screen.getByRole('button', { expanded: false }));

    expect(screen.getByLabelText('피드백: skip')).toBeInTheDocument();
  });
});
