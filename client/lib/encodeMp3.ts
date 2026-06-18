/**
 * encodeMp3 — 녹음 Blob(webm/ogg/Opus 등)을 mp3(`audio/mpeg`) Blob 으로 변환한다.
 *
 * `MediaRecorder` 는 mp3 인코딩을 지원하지 않으므로(webm/opus·ogg 만 가능), 백엔드가
 * mp3 만 받도록 하려면 클라이언트에서 디코딩→PCM→mp3 재인코딩이 필요하다. 흐름:
 *   1. Blob → ArrayBuffer
 *   2. AudioContext.decodeAudioData 로 PCM(Float32) 디코딩
 *   3. 16-bit PCM 으로 변환 후 lamejs(Mp3Encoder)로 mp3 프레임 인코딩
 *   4. 프레임들을 합쳐 `audio/mpeg` Blob 으로 반환
 *
 * 모노로 다운믹스해 단순화한다(감정 분석엔 채널 수가 중요치 않다). 디코딩 API 가
 * 없는 환경(테스트/구형 브라우저)에서는 호출자가 원본 Blob 으로 폴백할 수 있도록
 * 예외를 던진다.
 */
import { Mp3Encoder } from "lamejs";

const KBPS = 128;
/** lamejs 권장 샘플 블록 크기. */
const SAMPLE_BLOCK = 1152;

/** Float32 PCM(-1..1) → 16-bit signed PCM. */
function floatToInt16(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

/** AudioContext 생성 (webkit 접두사 포함 폴백). */
function makeAudioContext(): AudioContext {
  const Ctor =
    typeof AudioContext !== "undefined"
      ? AudioContext
      : (globalThis as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext;
  if (!Ctor) throw new Error("AudioContext unsupported");
  return new Ctor();
}

/**
 * 녹음 Blob 을 mp3 Blob 으로 변환한다.
 * @throws 디코딩/인코딩이 불가능한 환경이면 예외 — 호출자가 폴백 처리.
 */
export async function encodeMp3(input: Blob): Promise<Blob> {
  const arrayBuffer = await input.arrayBuffer();

  const ctx = makeAudioContext();
  let audioBuffer: AudioBuffer;
  try {
    audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));
  } finally {
    void ctx.close?.();
  }

  // 모노 다운믹스: 채널이 여럿이면 평균.
  const { numberOfChannels, length, sampleRate } = audioBuffer;
  const mono = new Float32Array(length);
  for (let ch = 0; ch < numberOfChannels; ch++) {
    const data = audioBuffer.getChannelData(ch);
    for (let i = 0; i < length; i++) mono[i] += data[i] / numberOfChannels;
  }

  const samples = floatToInt16(mono);
  const encoder = new Mp3Encoder(1, sampleRate, KBPS);
  const chunks: Uint8Array[] = [];

  for (let i = 0; i < samples.length; i += SAMPLE_BLOCK) {
    const block = samples.subarray(i, i + SAMPLE_BLOCK);
    const buf = encoder.encodeBuffer(block);
    if (buf.length > 0) chunks.push(new Uint8Array(buf));
  }
  const flush = encoder.flush();
  if (flush.length > 0) chunks.push(new Uint8Array(flush));

  return new Blob(chunks, { type: "audio/mpeg" });
}
