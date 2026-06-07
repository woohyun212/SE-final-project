/**
 * recommend.ts — 추천 결과 도메인 타입 + 백엔드 어댑터 (#45 차트 / #46 이유 카드 공유 계약)
 *
 * 설계 의도: 백엔드 `/recommend` 확정 응답(session_id / recommendations[] /
 * user_emotion / transcript / context / fallback_flags)을 프레젠테이션 컴포넌트가
 * 사용하는 도메인 타입으로 변환하는 단일 경계. 백엔드가 필드명을 바꿔도
 * `toRecommendResult()` 어댑터만 수정하면 소비처(VoiceCapture / recommend.tsx /
 * 차트 / 이유카드)는 영향이 없다.
 *
 * 주의: client/lib/api.ts 의 기존 `Track`(US-5 #20 리스트용, 최소 필드)은
 * 건드리지 않는다. 본 파일은 #45/#46 전용 확장 타입을 독립적으로 보유한다.
 */


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

/** 백엔드 context 필드 — 녹음 시점 상황 정보. */
export interface ContextResult {
  time_of_day: string | null;
  location: string | null;
  activity: string | null;
  /** 감정 레이블 → 확률값 매핑 (예: { "sad": 0.4, "happy": 0.2 }). */
  emotions: Record<string, number> | null;
}

/** 백엔드 fallback_flags — ML / context / reason 단계별 폴백 여부. */
export interface FallbackFlags {
  ml: boolean;
  context: boolean;
  reason: boolean;
}

/** `/recommend` 확장 응답 전체 (#38 RecommendResponse + 감정점 + 상황 + 폴백 플래그). */
export interface RecommendResult {
  /** 추천 세션 식별자 (백엔드 session_id). 피드백 API(#47 /feedback/*) 연동 키. */
  sessionId?: string;
  tracks: RecommendedTrack[];
  /** 사용자 감정 좌표 (음성 분석 결과). */
  userEmotion: EmotionPoint;
  /** STT 전사 텍스트 (#38 transcript). */
  transcript?: string | null;
  /** 녹음 시점 상황 정보 (백엔드 context). 제공 안 되면 null. */
  context?: ContextResult | null;
  /** ML / context / reason 단계별 폴백 여부 (백엔드 fallback_flags). */
  fallbackFlags?: FallbackFlags;
}

// ── 피드백 / 재생 / 이력 도메인 타입 (#47/#48/#50) ──────────────────────────
export type FeedbackType = 'like' | 'dislike';
export type PlaybackEvent = 'start' | 'end' | 'complete';

/** 추천 이력 항목의 피드백 엔트리 (백엔드 FeedbackEntry). */
export interface FeedbackEntry {
  track_id: string;
  title: string;
  artist: string;
  feedback_type: string;
}

/** 추천 이력 항목의 추천 곡 엔트리 (백엔드 RecommendedTrackEntry, 항상 반환). */
export interface RecommendedTrackEntry {
  track_id: string;
  title: string;
  artist: string;
  rank: number;
  score: number;
}

/** 추천 이력 항목 (백엔드 GET /history → HistoryItem[]). */
export interface HistoryItem {
  id: string;
  user_valence: number;
  user_energy: number;
  created_at: string;
  /** 해당 세션에서 추천된 곡 전체 (rank 순). 백엔드가 항상 반환. */
  recommended_tracks: RecommendedTrackEntry[];
  /** 해당 세션에서 사용자가 남긴 피드백. */
  feedbacks: FeedbackEntry[];
}

// ── 화면 간 추천 결과 전달 (sessionStorage) ──────────────────────────────────
//
// `/`(녹음) → `/recommend`(표시) 로 추천 결과를 넘기기 위한 1회성 핸드오프.
// 라우터 state 가 정적 export + 새로고침에 취약해 sessionStorage 를 사용한다.
// 새 녹음 시 같은 키를 덮어쓰므로 명시적 clear 없이도 항상 최신값이 유지된다.

const RECOMMEND_SESSION_KEY = 'se_emotion_music__recommend_result';

/** 추천 결과(도메인 RecommendResult)를 sessionStorage 에 저장 (SSR/제한 환경 가드). */
export function saveRecommendResult(result: RecommendResult): void {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(RECOMMEND_SESSION_KEY, JSON.stringify(result));
  } catch {
    // sessionStorage 접근 차단 시 조용히 무시 — 호출자는 저장 없이 진행.
  }
}

/** 저장된 추천 결과 로드. 없거나 파싱 실패 시 null. */
export function loadRecommendResult(): RecommendResult | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(RECOMMEND_SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as RecommendResult;
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
// 이 함수만 고치면 소비처(VoiceCapture / recommend.tsx / 차트 / 이유카드)는 영향이 없다.
//
// 확정 backend shape:
//   { session_id, recommendations: [{ track{track_id,title,artist,album,
//     duration_sec,preview_url?}, score, reason?|null, track_features{valence,energy} }],
//     user_emotion{valence,energy}, transcript?|null, context?|null, fallback_flags? }

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
 * - 확정 shape(`recommendations[]` + `track_features` + `user_emotion` + `context` + `fallback_flags`): 전 필드 매핑.
 * - 알 수 없는 형태: 빈 결과.
 */
export function toRecommendResult(raw: unknown): RecommendResult {
  const o = (raw ?? {}) as Record<string, unknown>;

  // 확정 shape
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
    // context: 백엔드가 제공하면 ContextResult 로, 없으면 null
    const rawCtx = o.context as Record<string, unknown> | null | undefined;
    const context: ContextResult | null = rawCtx
      ? {
          time_of_day: (rawCtx.time_of_day as string | null) ?? null,
          location: (rawCtx.location as string | null) ?? null,
          activity: (rawCtx.activity as string | null) ?? null,
          emotions: (rawCtx.emotions as Record<string, number> | null) ?? null,
        }
      : null;
    // fallback_flags: 백엔드가 제공하면 FallbackFlags 로, 없으면 undefined
    const rawFf = o.fallback_flags as Record<string, unknown> | null | undefined;
    const fallbackFlags: FallbackFlags | undefined = rawFf
      ? {
          ml: Boolean(rawFf.ml),
          context: Boolean(rawFf.context),
          reason: Boolean(rawFf.reason),
        }
      : undefined;
    return {
      sessionId: typeof o.session_id === 'string' ? o.session_id : undefined,
      tracks,
      userEmotion: { valence: ue.valence, energy: ue.energy },
      transcript: (o.transcript as string | null) ?? null,
      context,
      fallbackFlags,
    };
  }

  // 알 수 없는 shape: 빈 결과
  return {
    tracks: [],
    userEmotion: { valence: NEUTRAL, energy: NEUTRAL },
    transcript: null,
  };
}
