/**
 * AudioPlayer 컴포넌트 테스트 (#48, US-18).
 * preview_url 유무에 따른 활성/비활성 + 토글 콜백 + 상태 라벨 검증.
 */
import { render, screen, fireEvent } from '@testing-library/react';

import AudioPlayer from '../components/AudioPlayer';

describe('AudioPlayer', () => {
  it('previewUrl 없으면 비활성 + 사유 라벨', () => {
    render(<AudioPlayer previewUrl={null} playing={false} onToggle={jest.fn()} />);

    const btn = screen.getByRole('button', {
      name: '미리듣기가 제공되지 않는 곡입니다',
    });
    expect(btn).toBeDisabled();
  });

  it('previewUrl 있으면 활성 + 클릭 시 onToggle 호출', () => {
    const onToggle = jest.fn();
    render(
      <AudioPlayer
        previewUrl="https://cdn.example/p.mp3"
        playing={false}
        onToggle={onToggle}
      />,
    );

    const btn = screen.getByRole('button', { name: '미리듣기 재생' });
    expect(btn).toBeEnabled();
    expect(btn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(btn);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it('재생 중이면 일시정지 라벨 + aria-pressed', () => {
    render(
      <AudioPlayer
        previewUrl="https://cdn.example/p.mp3"
        playing={true}
        onToggle={jest.fn()}
      />,
    );

    const btn = screen.getByRole('button', { name: '일시정지' });
    expect(btn).toHaveAttribute('aria-pressed', 'true');
  });
});
