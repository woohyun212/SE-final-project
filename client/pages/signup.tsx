/**
 * signup.tsx — 회원가입 페이지
 *
 * 의존 lib (Worker B 작성):
 *   client/lib/api.ts   → signupApi(SignupRequest): Promise<TokenResponse>
 *   client/lib/auth.ts  → saveTokens(TokenResponse): void
 *   client/lib/validate.ts → validateEmail, validatePassword: (s: string) => ValidationResult
 *
 * POST /auth/signup { email, password }
 *   201 → saveTokens + router.push('/')
 *   409 → "이미 사용 중인 이메일입니다."
 *   422 → detail[0].msg
 *   network → "서버 연결 실패. 잠시 후 다시 시도해 주세요."
 */

import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useState, useCallback, FocusEvent, ChangeEvent, FormEvent } from 'react';

import { signupApi, ApiError } from '../lib/api';
import { saveTokens } from '../lib/auth';
import { validateEmail, validatePassword } from '../lib/validate';

import styles from '../styles/auth.module.css';

/* ── Font injection (Noto Sans KR — Google Fonts, self-contained <Head>) ── */
const FONT_URL =
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap';

/* ── Types ── */
interface FormState {
  email: string;
  password: string;
  passwordConfirm: string;
}

interface FieldErrors {
  email: string;
  password: string;
  passwordConfirm: string;
}

const EMPTY_ERRORS: FieldErrors = { email: '', password: '', passwordConfirm: '' };

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
export default function SignupPage() {
  const router = useRouter();

  const [form, setForm] = useState<FormState>({ email: '', password: '', passwordConfirm: '' });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>(EMPTY_ERRORS);
  const [apiError, setApiError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  /* ── Helpers ── */

  /** Validate a single field and update its error state. Returns the error string. */
  const validateField = useCallback(
    (name: keyof FormState, value: string, currentForm?: FormState): string => {
      const f = currentForm ?? form;

      if (name === 'email') {
        // validateEmail (lib/validate.ts) 가 빈값을 자체 처리 — 중복 체크 제거 (PR #67 품질 3).
        const result = validateEmail(value);
        return result.ok ? '' : (result.error ?? '올바른 이메일 형식이 아닙니다.');
      }

      if (name === 'password') {
        // validatePassword 가 빈값 자체 처리.
        const result = validatePassword(value);
        return result.ok ? '' : (result.error ?? '비밀번호 형식이 올바르지 않습니다.');
      }

      if (name === 'passwordConfirm') {
        if (!value) return '비밀번호 확인을 입력해 주세요.';
        if (value !== f.password) return '비밀번호가 일치하지 않습니다.';
        return '';
      }

      return '';
    },
    [form],
  );

  /** Validate all fields; returns true when all pass. */
  const validateAll = useCallback((): boolean => {
    const errors: FieldErrors = {
      email: validateField('email', form.email),
      password: validateField('password', form.password),
      passwordConfirm: validateField('passwordConfirm', form.passwordConfirm),
    };
    setFieldErrors(errors);
    return !errors.email && !errors.password && !errors.passwordConfirm;
  }, [form, validateField]);

  /* ── Event handlers ── */

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const { name, value } = e.target as { name: keyof FormState; value: string };
      const nextForm = { ...form, [name]: value };
      setForm(nextForm);
      // Clear api error on any change
      if (apiError) setApiError('');
      // PR #67 Bug 1: 두 setFieldErrors 호출을 하나로 병합 (이전 prev state 가 stale 해질 수 있음).
      const revalidateField = !!fieldErrors[name];
      const revalidateConfirm = name === 'password' && !!fieldErrors.passwordConfirm;
      if (revalidateField || revalidateConfirm) {
        setFieldErrors((prev) => {
          const next = { ...prev };
          if (revalidateField) {
            next[name] = validateField(name, value, nextForm);
          }
          if (revalidateConfirm) {
            next.passwordConfirm =
              nextForm.passwordConfirm !== value ? '비밀번호가 일치하지 않습니다.' : '';
          }
          return next;
        });
      }
    },
    [form, fieldErrors, apiError, validateField],
  );

  const handleBlur = useCallback(
    (e: FocusEvent<HTMLInputElement>) => {
      const { name, value } = e.target as { name: keyof FormState; value: string };
      // PR #67 품질 2: 빈 값이라도 *이미 에러가 표시되고 있던* 필드는 재검증 (UX 일관성).
      // 처음 진입 → 즉시 blur (한 번도 검증된 적 없는 빈 필드) 만 무시.
      setFieldErrors((prev) => {
        if (!value && !prev[name]) return prev;
        return {
          ...prev,
          [name]: validateField(name, value),
        };
      });
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
        const response = await signupApi({ email: form.email, password: form.password });
        saveTokens(response);
        await router.push('/');
      } catch (err: unknown) {
        // Typed API errors thrown by signupApi
        if (err instanceof ApiError) {
          if (err.status === 409) {
            setApiError('이미 사용 중인 이메일입니다.');
          } else if (err.status === 422) {
            setApiError(err.detail || '입력값을 확인해 주세요.');
          } else {
            setApiError(`오류가 발생했습니다. (${err.status})`);
          }
        } else if (err instanceof TypeError) {
          // fetch() network failure (offline, refused, etc.)
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
        <title>회원가입 — SE Final Project</title>
        <meta name="description" content="AI 음악 추천 시스템 회원가입" />
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
              <h1 className={styles.title}>회원가입</h1>
              <p className={styles.subtitle}>AI 감정 분석 음악 추천 시스템</p>
            </header>

            {/* ── Form ── */}
            <form
              className={styles.form}
              onSubmit={handleSubmit}
              noValidate
              aria-label="회원가입 폼"
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
                    autoComplete="new-password"
                    placeholder="영문 + 숫자 포함 8자 이상"
                    value={form.password}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    disabled={isSubmitting}
                    aria-invalid={!!fieldErrors.password}
                    aria-describedby={
                      fieldErrors.password ? 'password-error' : 'password-hint'
                    }
                    className={`${styles.input}${fieldErrors.password ? ' ' + styles.inputError : ''}`}
                  />
                </div>
                {fieldErrors.password ? (
                  <span id="password-error" role="alert" className={styles.error}>
                    {fieldErrors.password}
                  </span>
                ) : (
                  <span id="password-hint" className={styles.subtitle} style={{ fontSize: '0.72rem' }}>
                    영문자 1개 이상, 숫자 1개 이상, 최소 8자
                  </span>
                )}
              </div>

              {/* Password Confirm */}
              <div className={styles.field}>
                <label htmlFor="passwordConfirm" className={styles.label}>
                  비밀번호 확인
                </label>
                <div className={styles.inputWrap}>
                  <input
                    id="passwordConfirm"
                    name="passwordConfirm"
                    type="password"
                    required
                    autoComplete="new-password"
                    placeholder="비밀번호를 다시 입력하세요"
                    value={form.passwordConfirm}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    disabled={isSubmitting}
                    aria-invalid={!!fieldErrors.passwordConfirm}
                    aria-describedby={
                      fieldErrors.passwordConfirm ? 'passwordConfirm-error' : undefined
                    }
                    className={`${styles.input}${fieldErrors.passwordConfirm ? ' ' + styles.inputError : ''}`}
                  />
                </div>
                {fieldErrors.passwordConfirm && (
                  <span id="passwordConfirm-error" role="alert" className={styles.error}>
                    {fieldErrors.passwordConfirm}
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
                {isSubmitting ? '가입 중...' : '가입'}
              </button>
            </form>

            {/* ── Footer ── */}
            <footer className={styles.footer}>
              이미 계정이 있으신가요?
              <Link href="/login" className={styles.footerLink}>
                로그인
              </Link>
            </footer>

          </div>
        </div>
      </div>
    </>
  );
}

