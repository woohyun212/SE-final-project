/**
 * VoiceCapture — US-3 (이슈 #18) 음성 녹음 컴포넌트.
 *
 * useVoiceRecorder 훅으로 5초 녹음을 수행하고, 유효 녹음(≥2초)을 얻으면 자동으로
 * `POST /recommend` 로 업로드한다 (recommendApi). 권한 거부 / 너무 짧은 녹음 /
 * 업로드 실패 등 모든 경로에 대해 안내 메시지와 재시도 동선을 제공한다.
 *
 * 추천 결과 표시(곡 리스트 · 2D 차트)는 US-5 이후의 책임이므로, 여기서는 onResult
 * 콜백으로 결과를 위임하고 기본적으로 받은 곡 수만 확인 메시지로 보여준다.
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, recommendApi, type RecommendResponse } from "../lib/api";
import {
  MAX_DURATION_MS,
  MIN_DURATION_MS,
  useVoiceRecorder,
} from "../lib/useVoiceRecorder";

import styles from "../styles/voice.module.css";

type UploadStatus = "idle" | "uploading" | "success" | "error";

export interface VoiceCaptureProps {
  /** 업로드 성공 시 추천 결과를 상위로 전달 (US-5 곡 리스트 연결 지점). */
  onResult?: (result: RecommendResponse) => void;
}

const MAX_SECONDS = MAX_DURATION_MS / 1000;
const MIN_SECONDS = MIN_DURATION_MS / 1000;

export default function VoiceCapture({ onResult }: VoiceCaptureProps) {
  const recorder = useVoiceRecorder();
  const { status, elapsedMs, audioBlob, errorMessage, start, stop, reset } =
    recorder;

  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [trackCount, setTrackCount] = useState(0);

  const upload = useCallback(
    async (blob: Blob) => {
      setUploadStatus("uploading");
      setUploadError(null);
      try {
        const result = await recommendApi(blob);
        setTrackCount(result.tracks.length);
        setUploadStatus("success");
        onResult?.(result);
      } catch (err: unknown) {
        const message =
          err instanceof ApiError
            ? err.detail
            : "추천 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.";
        setUploadError(message);
        setUploadStatus("error");
      }
    },
    [onResult]
  );

  // 유효 녹음이 완료되면 자동 업로드.
  useEffect(() => {
    if (status === "recorded" && audioBlob && uploadStatus === "idle") {
      void upload(audioBlob);
    }
  }, [status, audioBlob, uploadStatus, upload]);

  /** 처음부터 다시 — 녹음 결과·업로드 상태 초기화 후 idle. */
  const handleRetry = useCallback(() => {
    setUploadStatus("idle");
    setUploadError(null);
    setTrackCount(0);
    reset();
  }, [reset]);

  /** 업로드만 재시도 (녹음 결과는 유지). */
  const handleRetryUpload = useCallback(() => {
    if (audioBlob) {
      setUploadStatus("idle");
      void upload(audioBlob);
    }
  }, [audioBlob, upload]);

  const elapsedSec = Math.min(elapsedMs / 1000, MAX_SECONDS);
  const progressPct = Math.min((elapsedMs / MAX_DURATION_MS) * 100, 100);
  const isRecording = status === "recording";
  const isRequesting = status === "requesting";

  return (
    <section className={styles.capture} aria-label="음성 녹음">
      {/* ── 시각 피드백 영역 (이퀄라이저 + 타이머) ── */}
      <div
        className={`${styles.stage}${isRecording ? " " + styles.stageActive : ""}`}
        aria-hidden="true"
      >
        <div className={styles.bars} data-recording={isRecording}>
          {Array.from({ length: 7 }).map((_, i) => (
            <span key={i} className={styles.bar} />
          ))}
        </div>
        {isRecording && (
          <div className={styles.timer}>
            {elapsedSec.toFixed(1)}
            <span className={styles.timerMax}> / {MAX_SECONDS.toFixed(0)}초</span>
          </div>
        )}
      </div>

      {/* ── 녹음 진행률 ── */}
      {isRecording && (
        <div
          className={styles.progress}
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={MAX_SECONDS}
          aria-valuenow={Number(elapsedSec.toFixed(1))}
          aria-label="녹음 진행률"
        >
          <div className={styles.progressFill} style={{ width: `${progressPct}%` }} />
        </div>
      )}

      {/* ── 상태 안내 (스크린리더 라이브) ── */}
      <div className={styles.statusArea} role="status" aria-live="polite">
        {status === "idle" && uploadStatus === "idle" && (
          <p className={styles.hint}>
            버튼을 누르고 최대 {MAX_SECONDS.toFixed(0)}초간 말해 보세요. 음성으로
            지금 감정을 분석합니다.
          </p>
        )}
        {isRequesting && <p className={styles.hint}>마이크 권한을 요청하는 중…</p>}
        {isRecording && <p className={styles.recordingLabel}>● 녹음 중…</p>}
        {uploadStatus === "uploading" && (
          <p className={styles.hint}>
            <span className={styles.spinner} aria-hidden="true" />
            음성을 분석하고 음악을 찾는 중…
          </p>
        )}
        {uploadStatus === "success" && (
          <p className={styles.success}>
            🎵 추천 {trackCount}곡을 받았어요!
          </p>
        )}
      </div>

      {/* ── 오류 / 안내 메시지 ── */}
      {status === "too_short" && (
        <div className={styles.notice} role="alert">
          녹음이 너무 짧아요. 최소 {MIN_SECONDS.toFixed(0)}초 이상 말한 뒤 다시
          시도해 주세요.
        </div>
      )}
      {status === "denied" && (
        <div className={styles.error} role="alert">
          {errorMessage}
        </div>
      )}
      {(status === "error" || status === "unsupported") && errorMessage && (
        <div className={styles.error} role="alert">
          {errorMessage}
        </div>
      )}
      {uploadStatus === "error" && uploadError && (
        <div className={styles.error} role="alert">
          {uploadError}
        </div>
      )}

      {/* ── 액션 버튼 ── */}
      <div className={styles.actions}>
        {(status === "idle" || status === "requesting") &&
          uploadStatus === "idle" && (
            <button
              type="button"
              className={styles.recordBtn}
              onClick={() => void start()}
              disabled={isRequesting}
              aria-busy={isRequesting}
            >
              <MicIcon />
              {isRequesting ? "준비 중…" : "녹음 시작"}
            </button>
          )}

        {isRecording && (
          <button
            type="button"
            className={`${styles.recordBtn} ${styles.stopBtn}`}
            onClick={stop}
          >
            <StopIcon />
            녹음 중지
          </button>
        )}

        {uploadStatus === "error" && (
          <button
            type="button"
            className={styles.recordBtn}
            onClick={handleRetryUpload}
          >
            전송 다시 시도
          </button>
        )}

        {(status === "too_short" ||
          status === "denied" ||
          status === "error" ||
          status === "unsupported" ||
          uploadStatus === "success" ||
          uploadStatus === "error") && (
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={handleRetry}
          >
            {uploadStatus === "success" ? "다시 녹음하기" : "처음부터 다시"}
          </button>
        )}
      </div>
    </section>
  );
}

/* ── Icons (inline SVG, currentColor) ── */
function MicIcon() {
  return (
    <svg
      className={styles.btnIcon}
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg
      className={styles.btnIcon}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}
