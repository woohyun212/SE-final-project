/**
 * normalizeApiBaseUrl 단위 테스트 — 백엔드 TLS 적용 대응(전부 https).
 *
 * 정책: 원격 호스트의 http 는 https 로 승격하고, 로컬 dev 호스트
 * (localhost/127.0.0.1/::1/*.local)는 그대로 둔다. 이미 https 면 유지.
 * 사용자의 .env 가 http 라도 코드가 런타임에 https 로 호출하도록 보장한다.
 */
import { normalizeApiBaseUrl } from "../lib/api";

describe("normalizeApiBaseUrl", () => {
  it("원격 http → https 로 승격", () => {
    expect(normalizeApiBaseUrl("http://backend.pongchi.kro.kr")).toBe(
      "https://backend.pongchi.kro.kr"
    );
  });

  it("이미 https 면 그대로 유지", () => {
    expect(normalizeApiBaseUrl("https://backend.pongchi.kro.kr")).toBe(
      "https://backend.pongchi.kro.kr"
    );
  });

  it("localhost http 는 유지 (로컬 dev)", () => {
    expect(normalizeApiBaseUrl("http://localhost:8000")).toBe(
      "http://localhost:8000"
    );
  });

  it("127.0.0.1 http 는 유지", () => {
    expect(normalizeApiBaseUrl("http://127.0.0.1:8000")).toBe(
      "http://127.0.0.1:8000"
    );
  });

  it("포트·경로를 보존하며 승격", () => {
    expect(normalizeApiBaseUrl("http://api.example.com:8080/v1")).toBe(
      "https://api.example.com:8080/v1"
    );
  });

  it("말미 슬래시는 제거", () => {
    expect(normalizeApiBaseUrl("https://backend.pongchi.kro.kr/")).toBe(
      "https://backend.pongchi.kro.kr"
    );
  });

  it("공백을 trim", () => {
    expect(normalizeApiBaseUrl("  http://backend.pongchi.kro.kr  ")).toBe(
      "https://backend.pongchi.kro.kr"
    );
  });

  it("*.local 호스트의 http 는 유지", () => {
    expect(normalizeApiBaseUrl("http://mymac.local:8000")).toBe(
      "http://mymac.local:8000"
    );
  });
});
