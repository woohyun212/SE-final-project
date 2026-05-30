/**
 * recommend.ts — 추천 결과 도메인 타입 + mock 데이터 (#45 차트 / #46 이유 카드 공유 계약)
 *
 * 설계 의도: 추후 백엔드 `/recommend` 확장 시 곧바로 연결되도록, 미래 백엔드
 * shape(`feature/issue-#38`: track_id/preview_url/transcript + recommendation.py
 * 의 valence/energy)을 예측해 타입을 확정한다. 실 API 연동 시 `MOCK_RECOMMEND_RESULT`
 * 를 `recommendApi` 응답으로 교체하고, 필요하면 `toRecommendResult()` 어댑터만 수정.
 *
 * 주의: client/lib/api.ts 의 기존 `Track`(US-5 #20 리스트용, 최소 필드)은
 * 건드리지 않는다. 본 파일은 #45/#46 전용 확장 타입을 독립적으로 보유한다.
 */

import type { RecommendResponse } from './api';

/** 추천 트랙 — 미래 백엔드 확장 응답 기준 (#38 + audio features). */
export interface RecommendedTrack {
  /** 백엔드 #38 Track.track_id */
  track_id: string;
  title: string;
  artist: string;
  album: string;
  duration_sec: number;
  /** 30초 미리듣기 URL (#38 Track.preview_url). 없을 수 있음. */
  preview_url?: string | null;
  /** 감정가(0..1): 0 부정 ↔ 1 긍정. recommendation.py 의 valence. (#45) */
  valence: number;
  /** 활기(0..1): 0 차분 ↔ 1 활기. recommendation.py 의 energy. (#45) */
  energy: number;
  /** LLM 생성 추천 이유 텍스트 (#46). 생성 전이면 null. */
  reason?: string | null;
}

/** 사용자 감정 좌표 — 차트의 기준점 (#45). */
export interface EmotionPoint {
  valence: number; // 0..1
  energy: number; // 0..1
  /** 표시 라벨 (예: "현재 감정"). */
  label?: string;
}

/** `/recommend` 확장 응답 전체 (#38 RecommendResponse + 감정점). */
export interface RecommendResult {
  tracks: RecommendedTrack[];
  /** 사용자 감정 좌표 (음성 분석 결과). */
  userEmotion: EmotionPoint;
  /** STT 전사 텍스트 (#38 transcript). */
  transcript?: string | null;
}

/**
 * 개발/프리뷰용 mock 추천 결과.
 * - 곡 6개를 valence×energy 4사분면에 고르게 분포 (차트 가시성 확보)
 * - 각 곡에 reason 텍스트 포함 (#46)
 * - userEmotion 1개
 *
 * 실 API 연동 시 이 상수를 `recommendApi()` 의 확장 응답으로 대체한다.
 */
export const MOCK_RECOMMEND_RESULT: RecommendResult = {
  userEmotion: { valence: 0.38, energy: 0.62, label: '현재 감정' },
  transcript: '오늘 하루가 길었지만 그래도 뭔가 해냈다는 기분이 들어.',
  tracks: [
    {
      track_id: 'mock-1',
      title: 'Sunrise Avenue',
      artist: 'Lumio',
      album: 'Daybreak',
      duration_sec: 213,
      preview_url: null,
      valence: 0.86, // 긍정·활기 (신남)
      energy: 0.81,
      reason:
        '목소리에서 느껴지는 성취감과 잘 어울리는 밝고 경쾌한 곡이에요. 하루를 마무리하며 기분을 끌어올리기 좋아요.',
    },
    {
      track_id: 'mock-2',
      title: 'Quiet Harbor',
      artist: 'Sea & Pine',
      album: 'Still Water',
      duration_sec: 247,
      preview_url: null,
      valence: 0.78, // 긍정·차분 (평온)
      energy: 0.27,
      reason:
        '편안하면서도 따뜻한 분위기라, 길었던 하루의 긴장을 천천히 풀어 주기에 알맞습니다.',
    },
    {
      track_id: 'mock-3',
      title: 'Paper Planes',
      artist: 'Mira Cho',
      album: 'Afternoons',
      duration_sec: 198,
      preview_url: null,
      valence: 0.55, // 중립 근처
      energy: 0.5,
      reason:
        '담담한 가사와 안정적인 리듬이 지금의 차분하면서도 살짝 들뜬 감정과 균형이 맞아요.',
    },
    {
      track_id: 'mock-4',
      title: 'Undertow',
      artist: 'Greyline',
      album: 'Pressure',
      duration_sec: 224,
      preview_url: null,
      valence: 0.22, // 부정·활기 (긴장)
      energy: 0.79,
      reason:
        '쌓인 피로와 긴장을 강한 비트로 분출하고 싶을 때 어울리는, 에너지 높은 트랙입니다.',
    },
    {
      track_id: 'mock-5',
      title: 'Late November',
      artist: 'Hanil',
      album: 'Greyscale',
      duration_sec: 269,
      preview_url: null,
      valence: 0.18, // 부정·차분 (우울)
      energy: 0.24,
      reason:
        '하루의 무게를 가만히 내려놓고 싶은 순간에, 잔잔하게 곁을 지켜 주는 곡이에요.',
    },
    {
      track_id: 'mock-6',
      title: 'Glasshouse',
      artist: 'Noon Tide',
      album: 'Translucent',
      duration_sec: 231,
      preview_url: null,
      valence: 0.62, // 긍정 쪽, 중간 에너지
      energy: 0.58,
      reason:
        '맑은 신스 톤이 성취감 뒤의 여운과 잘 맞아, 기분 좋게 마무리하도록 도와줍니다.',
    },
  ],
};

// ── 화면 간 추천 결과 전달 (sessionStorage) ──────────────────────────────────
//
// `/`(녹음) → `/recommend`(표시) 로 추천 결과를 넘기기 위한 1회성 핸드오프.
// 라우터 state 가 정적 export + 새로고침에 취약해 sessionStorage 를 사용한다.
// 새 녹음 시 같은 키를 덮어쓰므로 명시적 clear 없이도 항상 최신값이 유지된다.

const RECOMMEND_SESSION_KEY = 'se_emotion_music__recommend_result';

/** 추천 결과를 sessionStorage 에 저장 (SSR/제한 환경 가드). */
export function saveRecommendResult(result: RecommendResponse): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(RECOMMEND_SESSION_KEY, JSON.stringify(result));
  } catch {
    // sessionStorage 접근 차단 시 조용히 무시 — 호출자는 저장 없이 진행.
  }
}

/** 저장된 추천 결과 로드. 없거나 파싱 실패 시 null. */
export function loadRecommendResult(): RecommendResponse | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(RECOMMEND_SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as RecommendResponse;
  } catch {
    return null;
  }
}

/** 저장된 추천 결과 제거. */
export function clearRecommendResult(): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(RECOMMEND_SESSION_KEY);
  } catch {
    // ignore
  }
}

// ── 백엔드 응답 어댑터 (#107/#108 → 도메인 RecommendResult) ──────────────────
//
// 백엔드 `POST /recommend` 응답(snake_case·중첩)을 프레젠테이션 컴포넌트가 쓰는
// 도메인 타입으로 변환하는 **단일 경계**. 백엔드가 필드명을 바꿔도
// (예: emotion_vector → track_features, recommendation_id → session_id) 이 함수만
// 고치면 소비처(VoiceCapture / recommend.tsx / 차트 / 이유카드)는 영향이 없다.
//
// 현행 backend 머지본 기준 raw shape:
//   { session_id, recommendations: [{ track{track_id,title,artist,album,
//     duration_sec,preview_url?}, score, reason?, track_features{valence,energy} }],
//     user_emotion{valence,energy}, transcript?, context? }

/** 백엔드 RecommendResponse 의 개별 추천 항목 raw shape. 어댑터 입력 전용. */
interface RawRecommendationItem {
  track: {
    track_id: string;
    title: string;
    artist: string;
    album: string;
    duration_sec: number;
    preview_url?: string | null;
  };
  score: number;
  reason?: string | null;
  track_features: { valence: number; energy: number };
}

const NEUTRAL = 0.5;

/**
 * 백엔드 `/recommend` 응답(raw)을 도메인 `RecommendResult` 로 변환.
 *
 * - 새 shape(`recommendations[]` + `track_features` + `user_emotion`): 전 필드 매핑.
 * - 옛 shape(`{ tracks: [...] }`, transition fallback): valence/energy/reason 미제공이라
 *   중립값(0.5)/null 로 채움 — 리스트만 실데이터, 차트/이유는 호출자가 mock fallback.
 * - 알 수 없는 형태: 빈 결과.
 */
export function toRecommendResult(raw: unknown): RecommendResult {
  const o = (raw ?? {}) as Record<string, unknown>;

  // 새 shape (#107)
  if (Array.isArray(o.recommendations)) {
    const items = o.recommendations as RawRecommendationItem[];
    const tracks: RecommendedTrack[] = items.map((it) => ({
      track_id: it.track.track_id,
      title: it.track.title,
      artist: it.track.artist,
      album: it.track.album,
      duration_sec: it.track.duration_sec,
      preview_url: it.track.preview_url ?? null,
      valence: it.track_features.valence,
      energy: it.track_features.energy,
      reason: it.reason ?? null,
    }));
    const ue = (o.user_emotion ?? { valence: NEUTRAL, energy: NEUTRAL }) as {
      valence: number;
      energy: number;
    };
    return {
      tracks,
      userEmotion: { valence: ue.valence, energy: ue.energy },
      transcript: (o.transcript as string | null) ?? null,
    };
  }

  // 옛 shape (transition fallback)
  if (Array.isArray(o.tracks)) {
    const legacy = o.tracks as Array<{
      title: string;
      artist: string;
      album: string;
      duration_sec: number;
      track_id?: string;
    }>;
    const tracks: RecommendedTrack[] = legacy.map((t, i) => ({
      track_id: t.track_id ?? `legacy-${i}`,
      title: t.title,
      artist: t.artist,
      album: t.album,
      duration_sec: t.duration_sec,
      preview_url: null,
      valence: NEUTRAL,
      energy: NEUTRAL,
      reason: null,
    }));
    return {
      tracks,
      userEmotion: { valence: NEUTRAL, energy: NEUTRAL },
      transcript: null,
    };
  }

  return {
    tracks: [],
    userEmotion: { valence: NEUTRAL, energy: NEUTRAL },
    transcript: null,
  };
}
