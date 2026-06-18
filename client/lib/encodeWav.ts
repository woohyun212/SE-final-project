/**
 * encodeWav — 녹음 Blob(webm/ogg/Opus 등)을 WAV(`audio/wav`) Blob 으로 변환한다.
 *
 * `MediaRecorder` 는 WAV 인코딩을 지원하지 않지만(webm/opus·ogg 만 가능), 백엔드 ML
 * 서비스가 `soundfile`(libsndfile)로 오디오를 읽는데 libsndfile 은 mp3 를 지원하지
 * 않는다. WAV(PCM)는 라이브러리 없이 RIFF 헤더만 붙이면 되고 libsndfile 도 지원하므로
 * WAV 로 변환해 업로드한다. 흐름:
 *   1. Blob → ArrayBuffer
 *   2. AudioContext.decodeAudioData 로 PCM(Float32) 디코딩
 *   3. 모노 다운믹스 후 16-bit PCM RIFF/WAVE 컨테이너로 직렬화
 *
 * 디코딩 API 가 없는 환경(테스트/구형 브라우저)에서는 예외를 던져 호출자가 원본
 * Blob 으로 폴백할 수 있게 한다.
 */

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

/** Float32 PCM(모노) + 샘플레이트 → 16-bit PCM WAV ArrayBuffer. */
function pcmToWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const bytesPerSample = 2; // 16-bit
  const blockAlign = bytesPerSample; // 모노(채널 1)
  const dataSize = samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  const writeStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };

  // RIFF 헤더
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeStr(8, "WAVE");
  // fmt 청크
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true); // PCM fmt 크기
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // 채널 수(모노)
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true); // byte rate
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true); // bits per sample
  // data 청크
  writeStr(36, "data");
  view.setUint32(40, dataSize, true);

  // Float32(-1..1) → Int16 LE
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += bytesPerSample;
  }

  return buffer;
}

/**
 * 녹음 Blob 을 WAV Blob 으로 변환한다.
 * @throws 디코딩이 불가능한 환경이면 예외 — 호출자가 폴백 처리.
 */
export async function encodeWav(input: Blob): Promise<Blob> {
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

  return new Blob([pcmToWav(mono, sampleRate)], { type: "audio/wav" });
}
