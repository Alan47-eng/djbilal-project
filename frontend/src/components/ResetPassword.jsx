import React, { useState, useEffect } from 'react';
import api from '../api';
import { getApiErrorMessage } from '../utils/errors';
import { useLanguage } from '../context/LanguageContext';

export default function ResetPassword() {
  const { lang } = useLanguage();
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get('token') || '';
    setToken(t);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);
    if (!token) {
      setMessage(lang === 'ar' ? 'Geçersiz veya eksik token.' : 'Invalid or missing token.');
      return;
    }
    if (!password || password.length < 8) {
      setMessage(lang === 'ar' ? 'Parola en az 8 karakter olmalı.' : 'Password must be at least 8 characters.');
      return;
    }

    try {
      setLoading(true);
      await api.post('/password/confirm', { token, new_password: password });
      setMessage(lang === 'ar' ? 'Parolanız sıfırlandı. Giriş sayfasına yönlendiriliyorsunuz.' : 'Password reset successful. Redirecting to login...');
      setTimeout(() => (window.location.href = '/'), 2000);
    } catch (err) {
      setMessage(getApiErrorMessage(
        err,
        lang === 'ar' ? 'Sıfırlama başarısız.' : 'Reset failed.',
      ));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12 p-6 rounded-lg bg-slate-900 border border-slate-800">
      <h2 className="text-xl font-bold mb-4 text-white">{lang === 'ar' ? 'Şifre Sıfırlama' : 'Reset Password'}</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative w-full">
          <input
            type={showPassword ? 'text' : 'password'}
            placeholder={lang === 'ar' ? 'Yeni parola' : 'New password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 py-3 pl-12 pr-4 text-white"
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
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-purple-600 px-4 py-3 font-semibold text-white hover:bg-purple-700 disabled:opacity-60"
        >
          {loading ? (lang === 'ar' ? 'Gönderiliyor...' : 'Submitting...') : (lang === 'ar' ? 'Sıfırla' : 'Reset')}
        </button>
      </form>

      {message && (
        <div className="mt-4 p-3 rounded-md bg-slate-800 text-sm text-white">
          {message}
        </div>
      )}
    </div>
  );
}
