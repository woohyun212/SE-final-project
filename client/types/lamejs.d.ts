/**
 * lamejs 최소 타입 선언 (@types/lamejs 미제공).
 * encodeMp3.ts 에서 쓰는 Mp3Encoder 부분만 선언한다.
 */
declare module "lamejs" {
  export class Mp3Encoder {
    constructor(channels: number, sampleRate: number, kbps: number);
    encodeBuffer(left: Int16Array, right?: Int16Array): Int8Array;
    flush(): Int8Array;
  }
}
