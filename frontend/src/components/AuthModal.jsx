import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import api from '../api';
import { getApiErrorMessage } from '../utils/errors';

const AuthModal = ({ isOpen, initialMode = 'login', onClose, onSuccess }) => {
  const { lang } = useLanguage();
  const { login, register } = useAuth();
  const [activeTab, setActiveTab] = useState(initialMode);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resetMessage, setResetMessage] = useState(null);
  const [resetLoading, setResetLoading] = useState(false);
  const [verificationPending, setVerificationPending] = useState(false);
  const [verificationMessage, setVerificationMessage] = useState(null);
  const [verificationOriginEmail, setVerificationOriginEmail] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const t = {
    signIn: lang === 'ar' ? 'تسجيل الدخول' : 'Sign In',
    signUp: lang === 'ar' ? 'إنشاء حساب' : 'Sign Up',
    login: lang === 'ar' ? 'دخول' : 'Login',
    register: lang === 'ar' ? 'تسجيل' : 'Register',
    fullName: lang === 'ar' ? 'الاسم الكامل' : 'Full Name',
    email: lang === 'ar' ? 'البريد الإلكتروني' : 'Email',
    password: lang === 'ar' ? 'كلمة المرور' : 'Password',
    authFailed: lang === 'ar' ? 'فشل التحقق. حاول مرة أخرى.' : 'Authentication failed. Please try again.',
    wait: lang === 'ar' ? 'يرجى الانتظار...' : 'Please wait...',
    createAccount: lang === 'ar' ? 'إنشاء حساب' : 'Create Account',
    verificationSent: lang === 'ar'
      ? 'أدخل بريدك الإلكتروني ورمز التحقق المكوّن من 6 أرقام المرسل إليك.'
      : 'Enter your email and the 6-digit verification code sent to you.',
    verificationCode: lang === 'ar' ? 'رمز التحقق المكوّن من 6 أرقام' : '6-digit verification code',
    verify: lang === 'ar' ? 'تأكيد الرمز' : 'Verify code',
    resendVerification: lang === 'ar' ? 'إرسال رمز جديد' : 'Send a new code',
    resendSuccess: lang === 'ar'
      ? 'إذا كان هذا البريد مرتبطًا بتسجيل غير مكتمل، فسيتم إرسال رمز جديد.'
      : 'If this email has a pending registration, a new code will be sent.',
    codeSent: lang === 'ar' ? 'أرسلنا رمز تحقق إلى بريدك الإلكتروني.' : 'We sent a verification code to your email.',
  };

  useEffect(() => {
    if (!isOpen) return;
    setActiveTab(initialMode);
    setFullName('');
    setEmail('');
    setPassword('');
    setError(null);
    setLoading(false);
    setVerificationPending(false);
    setVerificationMessage(null);
    setVerificationOriginEmail('');
    setVerificationCode('');
  }, [isOpen, initialMode]);

  if (!isOpen) return null;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (activeTab === 'login') {
        const result = await login(email, password);
        if (!result.success) {
          setError(result.error || t.authFailed);
          return;
        }
        onSuccess(email);
        onClose();
        return;
      }

      const result = await register(email, password, fullName, lang);
      if (!result.success) {
        if (result.requiresEmailVerification) {
          setVerificationPending(true);
          setVerificationOriginEmail(email);
          setVerificationMessage(result.error || t.authFailed);
          return;
        }
        setError(result.error || t.authFailed);
        return;
      }
      setVerificationPending(true);
      setVerificationOriginEmail(email);
      setVerificationMessage(t.codeSent);
    } catch (err) {
      setError(getApiErrorMessage(err, t.authFailed));
    } finally {
      setLoading(false);
    }
  };

  const resendVerification = async () => {
    setVerificationMessage(null);
    try {
      setLoading(true);
      await api.post('/verification/resend', {
        original_email: verificationOriginEmail,
        email,
        lang,
      });
      setVerificationOriginEmail(email);
      setVerificationMessage(t.resendSuccess);
    } catch (err) {
      if (err.response?.status === 503) {
        setVerificationOriginEmail(email);
      }
      setVerificationMessage(getApiErrorMessage(err, t.authFailed));
    } finally {
      setLoading(false);
    }
  };

  const verifyEmailCode = async (event) => {
    event.preventDefault();
    setLoading(true);
    setVerificationMessage(null);
    try {
      await api.post('/verify-email', { email, code: verificationCode });
      const result = await login(email, password);
      if (!result.success) {
        setVerificationMessage(result.error || t.authFailed);
        return;
      }
      onSuccess(email);
      onClose();
    } catch (err) {
      setVerificationMessage(getApiErrorMessage(err, t.authFailed));
    } finally {
      setLoading(false);
    }
  };

  const requestReset = async () => {
    setResetMessage(null);
    if (!email) {
      setResetMessage(lang === 'ar' ? 'Lütfen önce e-posta girin.' : 'Please enter your email first.');
      return;
    }
    try {
      setResetLoading(true);
      await api.post('/password/request', { email, lang });
      setResetMessage(lang === 'ar'
        ? 'إذا كان البريد مرتبطًا بحساب، فسيتم إرسال رابط إعادة التعيين.'
        : 'If the email is associated with an account, a reset link will be sent.');
    } catch (err) {
      setResetMessage(getApiErrorMessage(
        err,
        lang === 'ar' ? 'تعذر إرسال البريد الإلكتروني. حاول مرة أخرى.' : 'Failed to send reset email. Try again.',
      ));
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-2xl font-bold text-white">
            {activeTab === 'login' ? t.signIn : t.signUp}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mb-6 grid grid-cols-2 rounded-lg bg-slate-800 p-1">
          <button
            type="button"
            onClick={() => {
              setActiveTab('login');
              setVerificationPending(false);
              setVerificationMessage(null);
            }}
            className={`rounded-md px-4 py-2 font-semibold ${
              activeTab === 'login'
                ? 'bg-purple-600 text-white'
                : 'text-slate-300 hover:text-white'
            }`}
          >
            {t.login}
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab('register');
              setVerificationPending(false);
              setVerificationMessage(null);
            }}
            className={`rounded-md px-4 py-2 font-semibold ${
              activeTab === 'register'
                ? 'bg-purple-600 text-white'
                : 'text-slate-300 hover:text-white'
            }`}
          >
            {t.register}
          </button>
        </div>

        {verificationPending ? (
          <form onSubmit={verifyEmailCode} className="space-y-4">
            <p className="text-sm text-slate-200">{t.verificationSent}</p>
            <label className="block space-y-1 text-sm text-slate-300">
              {t.email}
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white placeholder-slate-500"
              required
            />
            </label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              value={verificationCode}
              onChange={(event) => setVerificationCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder={t.verificationCode}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-center text-2xl tracking-[0.5em] text-white placeholder:text-sm placeholder:tracking-normal"
              required
            />
            {verificationMessage && (
              <div className="rounded-lg border border-slate-700 bg-slate-800 p-3 text-sm text-slate-200" role="status">
                {verificationMessage}
              </div>
            )}
            <button
              type="button"
              onClick={resendVerification}
              disabled={loading || !email}
              className="w-full rounded-lg border border-purple-500 px-4 py-3 font-semibold text-purple-200 hover:bg-purple-900/30 disabled:opacity-60"
            >
              {loading ? t.wait : t.resendVerification}
            </button>
            <button
              type="submit"
              disabled={loading || verificationCode.length !== 6}
              className="w-full rounded-lg bg-purple-600 px-4 py-3 font-semibold text-white hover:bg-purple-700 disabled:opacity-60"
            >
              {loading ? t.wait : t.verify}
            </button>
          </form>
        ) : <form onSubmit={handleSubmit} className="space-y-4">
          {activeTab === 'register' && (
            <input
              type="text"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder={t.fullName}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white placeholder-slate-500"
              required
            />
          )}
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder={t.email}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white placeholder-slate-500"
            required
          />
          <div className="relative w-full">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={t.password}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 py-3 pl-12 pr-4 text-white placeholder-slate-500"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((visible) => !visible)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              aria-pressed={showPassword}
              className="absolute left-[15px] top-1/2 z-10 -translate-y-1/2 cursor-pointer text-[#ccc] hover:text-white focus:outline-none focus:ring-2 focus:ring-purple-400"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                {showPassword ? (
                  <>
                    <path d="M3 3l18 18" />
                    <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
                    <path d="M9.9 5.2A10.7 10.7 0 0 1 12 5c5 0 8.3 4.5 9 7-.3 1.1-1 2.3-2 3.4" />
                    <path d="M6.2 6.2C3.9 7.6 2.4 10 2 12c.7 2.5 4 7 10 7 1.2 0 2.3-.2 3.3-.6" />
                  </>
                ) : (
                  <>
                    <path d="M2 12s3.3-7 10-7 10 7 10 7-3.3 7-10 7-10-7-10-7Z" />
                    <circle cx="12" cy="12" r="3" />
                  </>
                )}
              </svg>
            </button>
          </div>

          {activeTab === 'login' && (
            <div className="flex justify-end mt-2">
              <button
                type="button"
                onClick={requestReset}
                className="text-sm text-slate-300 hover:text-white underline"
                disabled={resetLoading}
              >
                {resetLoading
                  ? (lang === 'ar' ? 'جارٍ الإرسال...' : 'Sending...')
                  : (lang === 'ar' ? 'نسيت كلمة المرور؟' : 'Forgot Password?')}
              </button>
            </div>
          )}

          {resetMessage && (
            <div className="rounded-lg border border-green-600 bg-green-900/10 p-3 text-sm text-green-300 mt-3">
              {resetMessage}
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-600 bg-red-900/20 p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-purple-600 px-4 py-3 font-semibold text-white hover:bg-purple-700 disabled:opacity-60"
          >
            {loading
              ? t.wait
              : activeTab === 'login'
                ? t.signIn
                : t.createAccount}
          </button>
        </form>}
      </div>
    </div>
  );
};

export default AuthModal;
