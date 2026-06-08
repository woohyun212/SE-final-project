/**
 * validate.ts 단위 테스트.
 *
 * 대상 함수: validateEmail, validatePassword, validatePasswordMatch
 * 목표: 라인 및 브랜치 커버리지 최대화 (≥90%)
 */
import {
  validateEmail,
  validatePassword,
  validatePasswordMatch,
} from "../lib/validate";

// ── validateEmail ───────────────────────────────────────────────────────────

describe("validateEmail", () => {
  it("빈 문자열이면 ok=false 와 입력 요구 메시지를 반환한다", () => {
    const result = validateEmail("");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("이메일을 입력해 주세요.");
  });

  it("공백만 있는 문자열이면 ok=false 와 입력 요구 메시지를 반환한다", () => {
    const result = validateEmail("   ");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("이메일을 입력해 주세요.");
  });

  it("@ 가 없는 문자열이면 ok=false 와 형식 오류 메시지를 반환한다", () => {
    const result = validateEmail("invalidemail.com");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("올바른 이메일 형식이 아닙니다.");
  });

  it("도메인에 점이 없으면 ok=false 와 형식 오류 메시지를 반환한다", () => {
    const result = validateEmail("user@domain");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("올바른 이메일 형식이 아닙니다.");
  });

  it("공백이 포함된 이메일이면 ok=false 와 형식 오류 메시지를 반환한다", () => {
    const result = validateEmail("user @example.com");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("올바른 이메일 형식이 아닙니다.");
  });

  it("@ 가 두 개이면 ok=false 와 형식 오류 메시지를 반환한다", () => {
    const result = validateEmail("user@@example.com");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("올바른 이메일 형식이 아닙니다.");
  });

  it("올바른 이메일 형식이면 ok=true 를 반환한다", () => {
    const result = validateEmail("user@example.com");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("서브도메인이 있는 이메일도 ok=true 를 반환한다", () => {
    const result = validateEmail("user@mail.example.co.kr");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("숫자와 특수문자가 포함된 이메일도 ok=true 를 반환한다", () => {
    const result = validateEmail("user.name+tag@sub.domain.org");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });
});

// ── validatePassword ────────────────────────────────────────────────────────

describe("validatePassword", () => {
  it("빈 문자열이면 ok=false 와 입력 요구 메시지를 반환한다", () => {
    const result = validatePassword("");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("비밀번호를 입력해 주세요.");
  });

  it("8자 미만이면 ok=false 와 길이 오류 메시지를 반환한다", () => {
    const result = validatePassword("Ab1");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("비밀번호는 8자 이상이어야 합니다.");
  });

  it("정확히 7자이면 ok=false 와 길이 오류 메시지를 반환한다", () => {
    const result = validatePassword("Ab1cdef");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("비밀번호는 8자 이상이어야 합니다.");
  });

  it("8자 이상이지만 숫자가 없으면 ok=false 와 숫자 오류 메시지를 반환한다", () => {
    const result = validatePassword("abcdefgh");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("비밀번호에 숫자를 1개 이상 포함해야 합니다.");
  });

  it("8자 이상이지만 영문자가 없으면 ok=false 와 영문자 오류 메시지를 반환한다", () => {
    const result = validatePassword("12345678");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("비밀번호에 영문자를 1개 이상 포함해야 합니다.");
  });

  it("8자 이상이고 숫자와 영문자를 모두 포함하면 ok=true 를 반환한다", () => {
    const result = validatePassword("Password1");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("정확히 8자이고 조건을 모두 만족하면 ok=true 를 반환한다", () => {
    const result = validatePassword("abcde12f");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("대문자 영문자만 있어도 영문자 조건을 만족하여 ok=true 를 반환한다", () => {
    const result = validatePassword("ABCDE123");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("소문자 영문자만 있어도 영문자 조건을 만족하여 ok=true 를 반환한다", () => {
    const result = validatePassword("abcde123");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("특수문자가 포함되어도 다른 조건을 만족하면 ok=true 를 반환한다", () => {
    const result = validatePassword("p@ssw0rd!");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });
});

// ── validatePasswordMatch ───────────────────────────────────────────────────

describe("validatePasswordMatch", () => {
  it("두 비밀번호가 일치하지 않으면 ok=false 와 불일치 메시지를 반환한다", () => {
    const result = validatePasswordMatch("password1", "password2");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("비밀번호가 일치하지 않습니다.");
  });

  it("두 비밀번호가 일치하면 ok=true 를 반환한다", () => {
    const result = validatePasswordMatch("Password1", "Password1");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("둘 다 빈 문자열이면 일치하므로 ok=true 를 반환한다", () => {
    const result = validatePasswordMatch("", "");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });

  it("대소문자가 다르면 ok=false 와 불일치 메시지를 반환한다", () => {
    const result = validatePasswordMatch("Password1", "password1");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("비밀번호가 일치하지 않습니다.");
  });

  it("한쪽만 빈 문자열이면 ok=false 와 불일치 메시지를 반환한다", () => {
    const result = validatePasswordMatch("Password1", "");
    expect(result.ok).toBe(false);
    expect(result.error).toBe("비밀번호가 일치하지 않습니다.");
  });

  it("공백이 포함된 동일한 문자열이면 ok=true 를 반환한다", () => {
    const result = validatePasswordMatch("pass word1", "pass word1");
    expect(result.ok).toBe(true);
    expect(result.error).toBeUndefined();
  });
});
