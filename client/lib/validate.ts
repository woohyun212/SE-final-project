// ── Types ──────────────────────────────────────────────────────────────────

export interface ValidationResult {
  ok: boolean;
  error?: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

const ok: ValidationResult = { ok: true };

function fail(error: string): ValidationResult {
  return { ok: false, error };
}

// ── Validators ─────────────────────────────────────────────────────────────

/**
 * Validates an email address using a permissive RFC 5322 approximation.
 * Returns a Korean error message on failure.
 */
export function validateEmail(email: string): ValidationResult {
  if (email.trim() === "") return fail("이메일을 입력해 주세요.");

  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!pattern.test(email)) return fail("올바른 이메일 형식이 아닙니다.");

  return ok;
}

/**
 * Validates a password against the server-side rules:
 *   - 8 characters or more
 *   - At least one digit
 *   - At least one English letter
 *
 * Error messages are prioritised in the order above.
 */
export function validatePassword(password: string): ValidationResult {
  if (password === "") return fail("비밀번호를 입력해 주세요.");

  if (password.length < 8) return fail("비밀번호는 8자 이상이어야 합니다.");

  if (!/[0-9]/.test(password))
    return fail("비밀번호에 숫자를 1개 이상 포함해야 합니다.");

  if (!/[a-zA-Z]/.test(password))
    return fail("비밀번호에 영문자를 1개 이상 포함해야 합니다.");

  return ok;
}

/**
 * Checks that `confirm` matches `password`.
 * Both arguments are required to be non-empty before the match check — if
 * either is empty the caller should handle that via `validatePassword` first.
 */
export function validatePasswordMatch(
  password: string,
  confirm: string
): ValidationResult {
  if (password !== confirm) return fail("비밀번호가 일치하지 않습니다.");
  return ok;
}
