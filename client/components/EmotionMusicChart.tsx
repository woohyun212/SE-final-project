/**
 * EmotionMusicChart.tsx — 감정-음악 2D 산점도 차트 (#45 US-15)
 *
 * 순수 SVG 구현. 외부 차트 라이브러리 의존성 없음.
 * X축 = valence(0..1) "부정 ← 감정가 → 긍정"
 * Y축 = energy(0..1)  "차분 ← 활기 → 활발" (위로 갈수록 높음)
 *
 * 유닛 테스트 가능한 좌표 변환 헬퍼 `valenceEnergyToXY` 를 named export 로 제공.
 */

import { useState, useCallback } from 'react';
import type { RecommendedTrack, EmotionPoint } from '../lib/recommend';
import styles from '../styles/emotionChart.module.css';

/* ────────────────────────────────────────────────────────────
   Public types
   ──────────────────────────────────────────────────────────── */

export interface EmotionMusicChartProps {
  tracks: RecommendedTrack[];
  userEmotion: EmotionPoint;
  loading?: boolean;
  error?: string | null;
}

/* ────────────────────────────────────────────────────────────
   Coordinate helper (named export for unit tests)
   ──────────────────────────────────────────────────────────── */

/**
 * Convert a (valence, energy) point in [0..1]×[0..1] to SVG pixel coordinates.
 *
 * @param v   valence  0 = most negative  →  1 = most positive  (left → right)
 * @param e   energy   0 = calmest        →  1 = most energetic  (bottom → top, SVG inverted)
 * @param w   usable plot width  (viewBox width minus left+right padding)
 * @param h   usable plot height (viewBox height minus top+bottom padding)
 * @param pad padding object { left, top } — offset from SVG origin to plot origin
 * @returns   { x, y } in SVG coordinate space
 */
export function valenceEnergyToXY(
  v: number,
  e: number,
  w: number,
  h: number,
  pad: { left: number; top: number }
): { x: number; y: number } {
  const x = pad.left + v * w;
  // SVG y=0 is top; energy=1 (most active) maps to top → invert
  const y = pad.top + (1 - e) * h;
  return { x, y };
}

/* ────────────────────────────────────────────────────────────
   Okabe-Ito colorblind-safe palette + stroke patterns
   ──────────────────────────────────────────────────────────── */

/** Okabe-Ito 6-color palette. Color is NOT the sole differentiator — each
 *  track also gets a distinct strokeDasharray to remain distinguishable for
 *  deuteranopia/protanopia viewers (NFR 5.2). */
const TRACK_STYLES: Array<{ fill: string; strokeDasharray: string }> = [
  { fill: '#0072B2', strokeDasharray: 'none' },        // solid
  { fill: '#E69F00', strokeDasharray: '4 2' },         // dashed
  { fill: '#56B4E9', strokeDasharray: '2 2' },         // dotted
  { fill: '#D55E00', strokeDasharray: '6 2 2 2' },     // dash-dot
  { fill: '#009E73', strokeDasharray: '1 3' },         // sparse dot
  { fill: '#CC79A7', strokeDasharray: '8 2' },         // long dash
];

function trackStyle(index: number): { fill: string; strokeDasharray: string } {
  return TRACK_STYLES[index % TRACK_STYLES.length];
}

/* ────────────────────────────────────────────────────────────
   SVG layout constants
   ──────────────────────────────────────────────────────────── */

const VB_SIZE = 400;          // viewBox is VB_SIZE × VB_SIZE
const PAD = { left: 44, top: 28, right: 24, bottom: 44 } as const;
const PLOT_W = VB_SIZE - PAD.left - PAD.right;   // 332
const PLOT_H = VB_SIZE - PAD.top - PAD.bottom;   // 328

/* ────────────────────────────────────────────────────────────
   Sub-components (SVG)
   ──────────────────────────────────────────────────────────── */

/** Light quadrant grid lines */
function GridLines() {
  const midX = PAD.left + PLOT_W / 2;
  const midY = PAD.top + PLOT_H / 2;
  // minor grid every 25%
  const quarters = [0.25, 0.5, 0.75];
  return (
    <g aria-hidden="true">
      {/* minor horizontals */}
      {quarters.map((q) => {
        const y = PAD.top + (1 - q) * PLOT_H;
        return (
          <line
            key={`gh-${q}`}
            x1={PAD.left} y1={y}
            x2={PAD.left + PLOT_W} y2={y}
            stroke="var(--grid-color)"
            strokeWidth="1"
          />
        );
      })}
      {/* minor verticals */}
      {quarters.map((q) => {
        const x = PAD.left + q * PLOT_W;
        return (
          <line
            key={`gv-${q}`}
            x1={x} y1={PAD.top}
            x2={x} y2={PAD.top + PLOT_H}
            stroke="var(--grid-color)"
            strokeWidth="1"
          />
        );
      })}
      {/* center crosshair — slightly more prominent */}
      <line
        x1={midX} y1={PAD.top}
        x2={midX} y2={PAD.top + PLOT_H}
        stroke="var(--axis-color)"
        strokeWidth="1"
        strokeDasharray="4 3"
      />
      <line
        x1={PAD.left} y1={midY}
        x2={PAD.left + PLOT_W} y2={midY}
        stroke="var(--axis-color)"
        strokeWidth="1"
        strokeDasharray="4 3"
      />
    </g>
  );
}

/** Plot border + axes */
function Axes() {
  const x0 = PAD.left;
  const y0 = PAD.top;
  const x1 = PAD.left + PLOT_W;
  const y1 = PAD.top + PLOT_H;

  return (
    <g aria-hidden="true">
      {/* plot border box */}
      <rect
        x={x0} y={y0}
        width={PLOT_W} height={PLOT_H}
        fill="none"
        stroke="var(--axis-color)"
        strokeWidth="1.5"
        rx="2"
      />
      {/* X tick marks */}
      {[0, 0.25, 0.5, 0.75, 1].map((t) => {
        const x = x0 + t * PLOT_W;
        return (
          <line
            key={`xt-${t}`}
            x1={x} y1={y1}
            x2={x} y2={y1 + 5}
            stroke="var(--axis-color)"
            strokeWidth="1"
          />
        );
      })}
      {/* Y tick marks */}
      {[0, 0.25, 0.5, 0.75, 1].map((t) => {
        const y = y0 + (1 - t) * PLOT_H;
        return (
          <line
            key={`yt-${t}`}
            x1={x0 - 5} y1={y}
            x2={x0} y2={y}
            stroke="var(--axis-color)"
            strokeWidth="1"
          />
        );
      })}
    </g>
  );
}

/** Axis title labels */
function AxisLabels() {
  const centerX = PAD.left + PLOT_W / 2;
  const centerY = PAD.top + PLOT_H / 2;

  return (
    <g aria-hidden="true" fontSize="10" fill="var(--axis-label-color)" fontFamily="'Noto Sans KR', sans-serif">
      {/* X axis label (below plot) */}
      <text
        x={centerX}
        y={VB_SIZE - 6}
        textAnchor="middle"
        fontSize="10"
      >
        부정 ← 감정가 → 긍정
      </text>
      {/* Y axis label (rotated, left of plot) */}
      <text
        x={0}
        y={0}
        textAnchor="middle"
        fontSize="10"
        transform={`translate(11, ${centerY}) rotate(-90)`}
      >
        차분 ← 활기 → 활발
      </text>
      {/* X tick values */}
      {[0, 0.5, 1].map((t) => (
        <text
          key={`xv-${t}`}
          x={PAD.left + t * PLOT_W}
          y={PAD.top + PLOT_H + 15}
          textAnchor="middle"
          fontSize="9"
          opacity="0.7"
        >
          {t.toFixed(1)}
        </text>
      ))}
      {/* Y tick values */}
      {[0, 0.5, 1].map((t) => (
        <text
          key={`yv-${t}`}
          x={PAD.left - 8}
          y={PAD.top + (1 - t) * PLOT_H + 3.5}
          textAnchor="end"
          fontSize="9"
          opacity="0.7"
        >
          {t.toFixed(1)}
        </text>
      ))}
    </g>
  );
}

/** Faint 4-quadrant labels */
function QuadrantLabels() {
  const qx = PLOT_W / 4;
  const qy = PLOT_H / 4;
  const labels = [
    { label: '신남',  dx: qx * 3, dy: qy * 1 },    // top-right
    { label: '긴장',  dx: qx * 1, dy: qy * 1 },    // top-left
    { label: '평온',  dx: qx * 3, dy: qy * 3 },    // bottom-right
    { label: '우울',  dx: qx * 1, dy: qy * 3 },    // bottom-left
  ];
  return (
    <g
      aria-hidden="true"
      fontSize="13"
      fontWeight="600"
      fill="var(--quadrant-label-color)"
      fontFamily="'Noto Sans KR', sans-serif"
      letterSpacing="-0.02em"
    >
      {labels.map(({ label, dx, dy }) => (
        <text
          key={label}
          x={PAD.left + dx}
          y={PAD.top + dy}
          textAnchor="middle"
          dominantBaseline="middle"
        >
          {label}
        </text>
      ))}
    </g>
  );
}

/* ── Star polygon helper ── */
function starPoints(cx: number, cy: number, r: number, ir: number, n: number): string {
  const pts: string[] = [];
  for (let i = 0; i < n * 2; i++) {
    const angle = (Math.PI / n) * i - Math.PI / 2;
    const radius = i % 2 === 0 ? r : ir;
    pts.push(`${(cx + Math.cos(angle) * radius).toFixed(3)},${(cy + Math.sin(angle) * radius).toFixed(3)}`);
  }
  return pts.join(' ');
}

/** User emotion star marker */
function UserEmotionMarker({ emotion, onClick }: {
  emotion: EmotionPoint;
  onClick: () => void;
}) {
  const { x, y } = valenceEnergyToXY(emotion.valence, emotion.energy, PLOT_W, PLOT_H, PAD);
  const label = emotion.label ?? '현재 감정';
  const pts = starPoints(x, y, 10, 4.5, 5);

  return (
    <g>
      {/* glow halo */}
      <circle
        cx={x} cy={y} r={16}
        fill="var(--star-glow)"
        aria-hidden="true"
      />
      {/* star */}
      <polygon
        points={pts}
        fill="var(--accent-1)"
        stroke="#ffffff"
        strokeWidth="1.5"
        strokeLinejoin="round"
        role="img"
        aria-label={`${label}: valence ${emotion.valence.toFixed(2)} · energy ${emotion.energy.toFixed(2)}`}
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); }}
        style={{ cursor: 'pointer', outline: 'none' }}
      />
      {/* label above star */}
      <text
        x={x}
        y={y - 15}
        textAnchor="middle"
        fontSize="9.5"
        fontWeight="700"
        fill="var(--accent-1)"
        fontFamily="'Noto Sans KR', sans-serif"
        aria-hidden="true"
        style={{ pointerEvents: 'none' }}
      >
        {label}
      </text>
    </g>
  );
}

/** Track circle marker */
function TrackMarker({
  track,
  index,
  isActive,
  onActivate,
  onDeactivate,
}: {
  track: RecommendedTrack;
  index: number;
  isActive: boolean;
  onActivate: () => void;
  onDeactivate: () => void;
}) {
  const { x, y } = valenceEnergyToXY(track.valence, track.energy, PLOT_W, PLOT_H, PAD);
  const { fill, strokeDasharray } = trackStyle(index);
  const R = 7;

  const ariaLabel = `${track.title} · ${track.artist} · valence ${track.valence.toFixed(2)} · energy ${track.energy.toFixed(2)}`;

  return (
    <g>
      {/* active ring */}
      {isActive && (
        <circle
          cx={x} cy={y} r={R + 5}
          fill="none"
          stroke={fill}
          strokeWidth="1.5"
          opacity="0.35"
          aria-hidden="true"
        />
      )}
      <circle
        cx={x} cy={y} r={R}
        fill={fill}
        stroke="#ffffff"
        strokeWidth={strokeDasharray === 'none' ? 1.5 : 2}
        strokeDasharray={strokeDasharray === 'none' ? undefined : strokeDasharray}
        opacity={isActive ? 1 : 0.85}
        role="img"
        aria-label={ariaLabel}
        tabIndex={0}
        onMouseEnter={onActivate}
        onMouseLeave={onDeactivate}
        onFocus={onActivate}
        onBlur={onDeactivate}
        onKeyDown={(e) => { if (e.key === 'Escape') onDeactivate(); }}
        style={{ cursor: 'pointer', outline: 'none', transition: 'opacity 0.15s ease, r 0.15s ease' }}
      />
    </g>
  );
}

/* ────────────────────────────────────────────────────────────
   Tooltip (DOM overlay, positioned by percentage)
   ──────────────────────────────────────────────────────────── */

interface TooltipData {
  track: RecommendedTrack;
  /** position as fraction of SVG viewBox [0..1] */
  xFrac: number;
  yFrac: number;
}

function Tooltip({ data }: { data: TooltipData }) {
  const { track, xFrac, yFrac } = data;

  // flip horizontally if near right edge
  const flipX = xFrac > 0.65;
  const flipY = yFrac > 0.65;

  const style: React.CSSProperties = {
    position: 'absolute',
    top: flipY ? undefined : `${yFrac * 100}%`,
    bottom: flipY ? `${(1 - yFrac) * 100}%` : undefined,
    left: flipX ? undefined : `${xFrac * 100}%`,
    right: flipX ? `${(1 - xFrac) * 100}%` : undefined,
    transform: flipX && !flipY
      ? 'translateX(-100%) translateX(-8px) translateY(-50%)'
      : !flipX && !flipY
      ? 'translateX(8px) translateY(-50%)'
      : flipX && flipY
      ? 'translateX(-100%) translateX(-8px) translateY(8px)'
      : 'translateX(8px) translateY(8px)',
  };

  return (
    <div className={styles.tooltip} style={style} aria-hidden="true">
      <p className={styles.tooltipTitle}>{track.title}</p>
      <p className={styles.tooltipArtist}>{track.artist}</p>
      <p className={styles.tooltipMeta}>
        valence {track.valence.toFixed(2)} · energy {track.energy.toFixed(2)}
      </p>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Legend
   ──────────────────────────────────────────────────────────── */

function Legend() {
  const starPts = starPoints(0, 0, 7, 3, 5);
  return (
    <div className={styles.legend} aria-hidden="true">
      <span className={styles.legendItem}>
        <svg width="16" height="16" viewBox="-8 -8 16 16" aria-hidden="true">
          <circle cx="0" cy="0" r="7" fill="var(--star-glow)" />
          <polygon points={starPts} fill="var(--accent-1)" stroke="#fff" strokeWidth="1.2" />
        </svg>
        현재 감정 (★)
      </span>
      <span className={styles.legendItem}>
        <svg width="16" height="16" viewBox="-8 -8 16 16" aria-hidden="true">
          <circle cx="0" cy="0" r="6" fill="#0072B2" stroke="#fff" strokeWidth="1.5" />
        </svg>
        추천 곡 (●)
      </span>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Loading skeleton
   ──────────────────────────────────────────────────────────── */

function LoadingSkeleton() {
  return (
    <div className={styles.wrapper} aria-busy="true" aria-label="차트를 불러오는 중…">
      <div className={styles.skeletonWrap}>
        <div className={styles.skeletonPulse} />
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Error alert
   ──────────────────────────────────────────────────────────── */

function ErrorAlert({ message }: { message: string }) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.errorAlert} role="alert">
        <svg
          width="18" height="18"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
          focusable="false"
          style={{ flexShrink: 0, marginTop: 1 }}
        >
          <path d="M12 2 1 21h22L12 2Zm0 3.5L21 20H3L12 5.5ZM11 10v4h2v-4h-2Zm0 6v2h2v-2h-2Z" />
        </svg>
        {message}
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Main component
   ──────────────────────────────────────────────────────────── */

export default function EmotionMusicChart({
  tracks,
  userEmotion,
  loading = false,
  error = null,
}: EmotionMusicChartProps): JSX.Element {
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null);

  const handleActivate = useCallback((id: string) => setActiveTrackId(id), []);
  const handleDeactivate = useCallback(() => setActiveTrackId(null), []);

  /* Loading */
  if (loading) return <LoadingSkeleton />;

  /* Error */
  if (error) return <ErrorAlert message={error} />;

  /* Build aria-label summary for the chart container */
  const ariaLabel = [
    `감정-음악 2D 산점도. X축: 감정가(부정→긍정), Y축: 활기(차분→활발).`,
    `현재 감정: valence ${userEmotion.valence.toFixed(2)}, energy ${userEmotion.energy.toFixed(2)}.`,
    `추천 곡 ${tracks.length}개: ${tracks.map((t) => t.title).join(', ')}.`,
  ].join(' ');

  /* active track for tooltip */
  const activeTrack = activeTrackId != null
    ? tracks.find((t) => t.track_id === activeTrackId) ?? null
    : null;

  const activeTooltipData: TooltipData | null = activeTrack
    ? {
        track: activeTrack,
        xFrac: (valenceEnergyToXY(activeTrack.valence, activeTrack.energy, PLOT_W, PLOT_H, PAD).x) / VB_SIZE,
        yFrac: (valenceEnergyToXY(activeTrack.valence, activeTrack.energy, PLOT_W, PLOT_H, PAD).y) / VB_SIZE,
      }
    : null;

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <div className={styles.cardInner}>
          {/* Chart area: SVG + overlay tooltip */}
          <div
            className={styles.chartArea}
            role="img"
            aria-label={ariaLabel}
          >
            <svg
              className={styles.svg}
              viewBox={`0 0 ${VB_SIZE} ${VB_SIZE}`}
              aria-hidden="true"
              focusable="false"
            >
              <GridLines />
              <Axes />
              <AxisLabels />
              <QuadrantLabels />

              {/* Track markers */}
              {tracks.map((track, i) => (
                <TrackMarker
                  key={track.track_id}
                  track={track}
                  index={i}
                  isActive={activeTrackId === track.track_id}
                  onActivate={() => handleActivate(track.track_id)}
                  onDeactivate={handleDeactivate}
                />
              ))}

              {/* User emotion star — rendered on top */}
              <UserEmotionMarker
                emotion={userEmotion}
                onClick={() => handleDeactivate()}
              />
            </svg>

            {/* DOM tooltip overlay */}
            {activeTooltipData && <Tooltip data={activeTooltipData} />}
          </div>

          {/* Legend */}
          <Legend />
        </div>
      </div>
    </div>
  );
}
