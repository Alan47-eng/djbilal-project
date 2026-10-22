import React, { useEffect, useState } from 'react';
import api from '../api';
import { getApiErrorMessage } from '../utils/errors';
import { useLanguage } from '../context/LanguageContext';

export default function VerifyEmail() {
  const { lang } = useLanguage();
  const [message, setMessage] = useState(
    lang === 'ar' ? 'جارٍ التحقق من بريدك الإلكتروني...' : 'Verifying your email...',
  );
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token');
    if (!token) {
      setMessage(lang === 'ar' ? 'رابط التحقق غير صالح أو منتهي الصلاحية.' : 'Invalid or expired verification link.');
      return;
    }

    api.post('/verify-email', { token })
      .then(() => {
        setSuccess(true);
        setMessage(lang === 'ar' ? 'تم التحقق من بريدك الإلكتروني. يمكنك الآن تسجيل الدخول.' : 'Your email is verified. You can now log in.');
      })
      .catch((error) => {
        setMessage(getApiErrorMessage(
          error,
          lang === 'ar' ? 'تعذر التحقق من بريدك الإلكتروني.' : 'Could not verify your email.',
        ));
      });
  }, [lang]);

  return (
    <main className="mx-auto mt-12 max-w-md rounded-lg border border-slate-800 bg-slate-900 p-6">
      <h1 className="mb-4 text-xl font-bold text-white">
        {lang === 'ar' ? 'التحقق من البريد الإلكتروني' : 'Email verification'}
      </h1>
      <p className="text-sm text-slate-200">{message}</p>
      {success && (
        <a
          href="/"
          className="mt-6 inline-block rounded-lg bg-purple-600 px-4 py-3 font-semibold text-white hover:bg-purple-700"
        >
          {lang === 'ar' ? 'العودة لتسجيل الدخول' : 'Return to login'}
        </a>
      )}
    </main>
  );
}
