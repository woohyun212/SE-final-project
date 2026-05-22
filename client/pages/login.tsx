/**
 * login.tsx — 로그인 페이지
 *
 * 의존 lib:
 *   client/lib/api.ts        → loginApi(LoginRequest): Promise<TokenResponse>
 *                              ApiError (class: { status, detail })
 *   client/lib/auth.ts       → saveTokens(TokenResponse): void
 *   client/lib/useAuthGuard.ts → useGuestGuard(): void  (Worker B 작성 예정)
 *
 * POST /auth/login { email, password }
 *   200 → saveTokens + router.push('/')
 *   401 → backend detail 그대로 표시
 *   422 → detail[0].msg (apiFetch 내부에서 normalise)
 *   network (status 0) → "서버 연결 실패. 잠시 후 다시 시도해 주세요."
 */

import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useState, useCallback, FocusEvent, ChangeEvent, FormEvent } from 'react';

import { loginApi, ApiError } from '../lib/api';
import { saveTokens } from '../lib/auth';
import { useGuestGuard } from '../lib/useAuthGuard';

import styles from '../styles/auth.module.css';

/* ── Font injection (Noto Sans KR — Google Fonts, self-contained <Head>) ── */
const FONT_URL =
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap';

/* ── Types ── */
interface FormState {
  email: string;
  password: string;
}

interface FieldErrors {
  email: string;
  password: string;
}

const EMPTY_ERRORS: FieldErrors = { email: '', password: '' };

/* ── Equalizer icon (5 bars, animated via CSS) ── */
function EqualizerIcon() {
  return (
    <div className={styles.iconWrap} aria-hidden="true">
      <span className={styles.bar} />
      <span className={styles.bar} />
      <span className={styles.bar} />
      <span className={styles.bar} />
      <span className={styles.bar} />
    </div>
  );
}

/* ── Main page component ── */
export default function LoginPage() {
  const router = useRouter();

  // 이미 로그인된 사용자는 / 로 리다이렉트 (Worker B 의 hook)
  useGuestGuard();

  const [form, setForm] = useState<FormState>({ email: '', password: '' });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>(EMPTY_ERRORS);
  const [apiError, setApiError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  /* ── Helpers ── */

  /**
   * 로그인은 클라이언트 측에서 형식 검증을 하지 않음.
   * 빈 값 여부만 확인하고 서버 응답을 신뢰한다.
   */
  const validateField = useCallback(
    (name: keyof FormState, value: string): string => {
      if (name === 'email') {
        return value.trim() ? '' : '이메일을 입력해 주세요.';
      }
      if (name === 'password') {
        return value ? '' : '비밀번호를 입력해 주세요.';
      }
      return '';
    },
    [],
  );

  /** 모든 필드 검증; 모두 통과하면 true 반환. */
  const validateAll = useCallback((): boolean => {
    const errors: FieldErrors = {
      email: validateField('email', form.email),
      password: validateField('password', form.password),
    };
    setFieldErrors(errors);
    return !errors.email && !errors.password;
  }, [form, validateField]);

  /* ── Event handlers ── */

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { name, value } = e.target as { name: keyof FormState; value: string };
      const nextForm = { ...form, [name]: value };
      setForm(nextForm);
      // 변경 시 API 에러 초기화
      if (apiError) setApiError('');
      // 이미 에러가 표시된 필드는 실시간 재검증
      if (fieldErrors[name]) {
        setFieldErrors((prev) => ({
          ...prev,
          [name]: validateField(name, value),
        }));
      }
    },
    [form, fieldErrors, apiError, validateField],
  );

  const handleBlur = useCallback(
    (e: FocusEvent<HTMLInputElement>) => {
      const { name, value } = e.target as { name: keyof FormState; value: string };
      if (!value) return; // 미입력 상태에서 blur 시 나그 메시지 표시 안 함
      setFieldErrors((prev) => ({
        ...prev,
        [name]: validateField(name, value),
      }));
    },
    [validateField],
  );

  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setApiError('');

      if (!validateAll()) return;

      setIsSubmitting(true);
      try {
        const response = await loginApi({ email: form.email, password: form.password });
        saveTokens(response);
        await router.push('/');
      } catch (err: unknown) {
        if (isApiError(err)) {
          if (err.status === 401) {
            setApiError(
              err.detail || '이메일 또는 비밀번호가 올바르지 않습니다.',
            );
          } else if (err.status === 0) {
            // apiFetch 가 network failure 를 ApiError(0, …) 로 wrap
            setApiError('서버 연결 실패. 잠시 후 다시 시도해 주세요.');
          } else if (err.status === 422) {
            setApiError(err.detail || '입력값을 확인해 주세요.');
          } else {
            setApiError(`오류가 발생했습니다. (${err.status})`);
          }
        } else if (err instanceof TypeError) {
          // fetch() 수준 네트워크 실패 (방어 코드 — apiFetch 가 이미 wrap)
          setApiError('서버 연결 실패. 잠시 후 다시 시도해 주세요.');
        } else {
          setApiError('알 수 없는 오류가 발생했습니다.');
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [form, validateAll, router],
  );

  /* ── Render ── */
  return (
    <>
      <Head>
        <title>로그인 — AI 감정 분석 음악 추천 시스템</title>
        <meta name="description" content="AI 음악 추천 시스템 로그인" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href={FONT_URL} rel="stylesheet" />
        <style>{`body { font-family: 'Noto Sans KR', system-ui, sans-serif; }`}</style>
      </Head>

      <div className={styles.page}>
        <div className={styles.card} role="main">
          {/* accent line rendered by card::before in CSS */}
          <div className={styles.cardInner}>

            {/* ── Header ── */}
            <header className={styles.header}>
              <EqualizerIcon />
              <h1 className={styles.title}>로그인</h1>
              <p className={styles.subtitle}>AI 감정 분석 음악 추천 시스템</p>
            </header>

            {/* ── Form ── */}
            <form
              className={styles.form}
              onSubmit={handleSubmit}
              noValidate
              aria-label="로그인 폼"
            >
              {/* Email */}
              <div className={styles.field}>
                <label htmlFor="email" className={styles.label}>
                  이메일
                </label>
                <div className={styles.inputWrap}>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    autoComplete="email"
                    placeholder="example@email.com"
                    value={form.email}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    disabled={isSubmitting}
                    aria-invalid={!!fieldErrors.email}
                    aria-describedby={fieldErrors.email ? 'email-error' : undefined}
                    className={`${styles.input}${fieldErrors.email ? ' ' + styles.inputError : ''}`}
                  />
                </div>
                {fieldErrors.email && (
                  <span id="email-error" role="alert" className={styles.error}>
                    {fieldErrors.email}
                  </span>
                )}
              </div>

              {/* Password */}
              <div className={styles.field}>
                <label htmlFor="password" className={styles.label}>
                  비밀번호
                </label>
                <div className={styles.inputWrap}>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    required
                    autoComplete="current-password"
                    placeholder="비밀번호를 입력하세요"
                    value={form.password}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    disabled={isSubmitting}
                    aria-invalid={!!fieldErrors.password}
                    aria-describedby={fieldErrors.password ? 'password-error' : undefined}
                    className={`${styles.input}${fieldErrors.password ? ' ' + styles.inputError : ''}`}
                  />
                </div>
                {fieldErrors.password && (
                  <span id="password-error" role="alert" className={styles.error}>
                    {fieldErrors.password}
                  </span>
                )}
              </div>

              {/* API / global error */}
              {apiError && (
                <div role="alert" className={styles.formError}>
                  {apiError}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={isSubmitting}
                aria-busy={isSubmitting}
                className={`${styles.submit}${isSubmitting ? ' ' + styles.submitDisabled : ''}`}
              >
                {isSubmitting && <span className={styles.spinner} aria-hidden="true" />}
                {isSubmitting ? '로그인 중...' : '로그인'}
              </button>
            </form>

            {/* ── Footer ── */}
            <footer className={styles.footer}>
              아직 계정이 없으신가요?
              <Link href="/signup" className={styles.footerLink}>
                회원가입
              </Link>
            </footer>

          </div>
        </div>
      </div>
    </>
  );
}

/* ── Type guard for ApiError ── */
function isApiError(err: unknown): err is ApiError {
  return (
    typeof err === 'object' &&
    err !== null &&
    typeof (err as ApiError).status === 'number' &&
    typeof (err as ApiError).detail === 'string'
  );
}
