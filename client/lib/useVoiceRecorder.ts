/**
 * useVoiceRecorder — US-3 (이슈 #18) 음성 녹음 훅.
 *
 * `navigator.mediaDevices.getUserMedia({ audio: true })` 로 마이크 스트림을 얻고
 * `MediaRecorder` 로 녹음한다. SRS FR2.1~FR2.4 / Acceptance Criteria 대응:
 *   - 마이크 권한 요청 (거부 시 'denied')
 *   - 녹음 중 경과 시간(elapsedMs) 노출 → 타이머/진행률 시각 피드백
 *   - 5초(MAX_DURATION_MS) 경과 시 자동 종료
 *   - 2초(MIN_DURATION_MS) 미만이면 'too_short' 로 처리하고 결과 폐기 (재시도 안내)
 *
 * 녹음 원본은 이 훅이 보관하지 않는다 — 호출자가 audioBlob 을 업로드한 뒤
 * reset() 으로 폐기한다 (NFR3.2 음성 원본 즉시 폐기 정책의 클라이언트 측 협조).
 *
 * audioBlob 은 항상 mp3(`audio/mpeg`)로 노출한다 — MediaRecorder 녹음 원본(webm/ogg)을
 * encodeMp3 로 재인코딩한다. 디코딩/인코딩이 불가능한 환경에서는 원본 Blob 으로 폴백.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { encodeMp3 } from "./encodeMp3";

export const MAX_DURATION_MS = 5000;
export const MIN_DURATION_MS = 2000;

export type RecorderStatus =
  | "idle" // 시작 전
  | "requesting" // 마이크 권한 요청 중
  | "recording" // 녹음 중
  | "encoding" // 녹음 완료 — mp3 변환 중
  | "recorded" // 녹음 완료 (유효 — audioBlob 사용 가능)
  | "too_short" // 2초 미만 — 재시도 안내
  | "denied" // 권한 거부
  | "unsupported" // 브라우저/환경이 녹음 API 미지원
  | "error"; // 그 외 오류

export interface VoiceRecorder {
  status: RecorderStatus;
  /** 녹음 경과 시간(ms). recording 상태에서 ~100ms 주기로 갱신. */
  elapsedMs: number;
  /** 유효 녹음 결과 mp3 Blob (status === 'recorded' 일 때만 non-null). */
  audioBlob: Blob | null;
  /** 사용자에게 보여줄 오류 메시지 (denied/error/unsupported 시). */
  errorMessage: string | null;
  /** 녹음 시작 (권한 요청 포함). */
  start: () => Promise<void>;
  /** 녹음 수동 종료. */
  stop: () => void;
  /** idle 로 초기화 — 결과 폐기 후 재시도. */
  reset: () => void;
}

/** MediaRecorder 가 지원하는 첫 번째 mimeType 을 고른다 (없으면 브라우저 기본값). */
function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg"];
  for (const type of candidates) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return undefined;
}

export function useVoiceRecorder(): VoiceRecorder {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoStopRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimers = useCallback(() => {
    if (tickRef.current !== null) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    if (autoStopRef.current !== null) {
      clearTimeout(autoStopRef.current);
      autoStopRef.current = null;
    }
  }, []);

  /** 마이크 트랙을 모두 정지해 OS 의 녹음 표시등을 끈다. */
  const releaseStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    clearTimers();
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop(); // → onstop 에서 결과 판정
    }
  }, [clearTimers]);

  const start = useCallback(async () => {
    // 이미 진행 중이면 무시.
    if (status === "requesting" || status === "recording") return;

    setErrorMessage(null);
    setAudioBlob(null);
    setElapsedMs(0);

    // 환경 지원 여부 확인.
    const md =
      typeof navigator !== "undefined" ? navigator.mediaDevices : undefined;
    if (!md || typeof md.getUserMedia !== "function" || typeof MediaRecorder === "undefined") {
      setStatus("unsupported");
      setErrorMessage("이 환경에서는 녹음을 지원하지 않습니다.");
      return;
    }

    setStatus("requesting");

    let stream: MediaStream;
    try {
      stream = await md.getUserMedia({ audio: true });
    } catch (err: unknown) {
      const name = err instanceof Error ? err.name : "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setStatus("denied");
        setErrorMessage(
          "마이크 권한이 거부되었습니다. 브라우저/시스템 설정에서 마이크 접근을 허용해 주세요."
        );
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setStatus("error");
        setErrorMessage("마이크 장치를 찾을 수 없습니다.");
      } else {
        setStatus("error");
        setErrorMessage("마이크를 시작할 수 없습니다. 잠시 후 다시 시도해 주세요.");
      }
      return;
    }

    streamRef.current = stream;
    chunksRef.current = [];

    const mimeType = pickMimeType();
    const recorder = new MediaRecorder(
      stream,
      mimeType ? { mimeType } : undefined
    );
    recorderRef.current = recorder;

    recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data && event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstop = () => {
      clearTimers();
      const durationMs = Date.now() - startTimeRef.current;
      releaseStream();

      const rawBlob = new Blob(chunksRef.current, {
        type: mimeType ?? "audio/webm",
      });
      chunksRef.current = [];

      if (durationMs < MIN_DURATION_MS) {
        // 너무 짧은 녹음 — 결과 폐기, 재시도 안내.
        setAudioBlob(null);
        setStatus("too_short");
        return;
      }

      // 녹음 원본(webm/ogg)을 mp3 로 재인코딩 후 노출. 변환 실패 시 원본으로 폴백.
      setStatus("encoding");
      encodeMp3(rawBlob)
        .then((mp3) => {
          setAudioBlob(mp3);
          setStatus("recorded");
        })
        .catch(() => {
          setAudioBlob(rawBlob);
          setStatus("recorded");
        });
    };

    recorder.onerror = () => {
      clearTimers();
      releaseStream();
      setStatus("error");
      setErrorMessage("녹음 중 오류가 발생했습니다.");
    };

    startTimeRef.current = Date.now();
    recorder.start();
    setStatus("recording");
    setElapsedMs(0);

    // 경과 시간 갱신 (UI 타이머/진행률).
    tickRef.current = setInterval(() => {
      setElapsedMs(Date.now() - startTimeRef.current);
    }, 100);

    // 5초 자동 종료.
    autoStopRef.current = setTimeout(() => {
      stop();
    }, MAX_DURATION_MS);
  }, [status, clearTimers, releaseStream, stop]);

  const reset = useCallback(() => {
    clearTimers();
    releaseStream();
    recorderRef.current = null;
    chunksRef.current = [];
    setAudioBlob(null);
    setElapsedMs(0);
    setErrorMessage(null);
    setStatus("idle");
  }, [clearTimers, releaseStream]);

  // 언마운트 시 자원 정리.
  useEffect(() => {
    return () => {
      clearTimers();
      releaseStream();
    };
  }, [clearTimers, releaseStream]);

  return {
    status,
    elapsedMs,
    audioBlob,
    errorMessage,
    start,
    stop,
    reset,
  };
}
