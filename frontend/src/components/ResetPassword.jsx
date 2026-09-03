import React, { useState, useEffect } from 'react';
import api from '../api';
import { useLanguage } from '../context/LanguageContext';

export default function ResetPassword() {
  const { lang } = useLanguage();
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
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
      setMessage(err.response?.data?.detail || (lang === 'ar' ? 'Sıfırlama başarısız.' : 'Reset failed.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-12 p-6 rounded-lg bg-slate-900 border border-slate-800">
      <h2 className="text-xl font-bold mb-4 text-white">{lang === 'ar' ? 'Şifre Sıfırlama' : 'Reset Password'}</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="password"
          placeholder={lang === 'ar' ? 'Yeni parola' : 'New password'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white"
          required
        />
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
