/**
 * #45 EmotionMusicChart — valenceEnergyToXY 좌표 변환 단위 테스트.
 * SVG 좌표계(y=0 상단)에서 energy 가 위로 증가하도록 반전되는지 검증.
 */
import { valenceEnergyToXY } from '../components/EmotionMusicChart';

const W = 300;
const H = 300;
const PAD = { left: 40, top: 20 };

describe('valenceEnergyToXY', () => {
  it('valence 0 → 왼쪽 끝(x=pad.left)', () => {
    expect(valenceEnergyToXY(0, 0.5, W, H, PAD).x).toBe(PAD.left);
  });

  it('valence 1 → 오른쪽 끝(x=pad.left+w)', () => {
    expect(valenceEnergyToXY(1, 0.5, W, H, PAD).x).toBe(PAD.left + W);
  });

  it('energy 1(최대 활기) → 상단(y=pad.top)으로 반전', () => {
    expect(valenceEnergyToXY(0.5, 1, W, H, PAD).y).toBe(PAD.top);
  });

  it('energy 0(최소 활기) → 하단(y=pad.top+h)', () => {
    expect(valenceEnergyToXY(0.5, 0, W, H, PAD).y).toBe(PAD.top + H);
  });

  it('중앙(0.5, 0.5) → 정확히 중앙 좌표', () => {
    const { x, y } = valenceEnergyToXY(0.5, 0.5, W, H, PAD);
    expect(x).toBe(PAD.left + W / 2);
    expect(y).toBe(PAD.top + H / 2);
  });

  it('energy 증가 → y 감소 (단조 반전)', () => {
    const low = valenceEnergyToXY(0.5, 0.2, W, H, PAD).y;
    const high = valenceEnergyToXY(0.5, 0.8, W, H, PAD).y;
    expect(high).toBeLessThan(low);
  });
});
