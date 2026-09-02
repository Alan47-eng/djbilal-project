import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import api from '../api';

const AuthModal = ({ isOpen, initialMode = 'login', onClose, onSuccess }) => {
  const { lang } = useLanguage();
  const { login, register } = useAuth();
  const [activeTab, setActiveTab] = useState(initialMode);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resetMessage, setResetMessage] = useState(null);
  const [resetLoading, setResetLoading] = useState(false);
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
  };

  useEffect(() => {
    if (!isOpen) return;
    setActiveTab(initialMode);
    setFullName('');
    setEmail('');
    setPassword('');
    setError(null);
    setLoading(false);
  }, [isOpen, initialMode]);

  if (!isOpen) return null;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (activeTab === 'login') {
        const success = await login(email, password);
        if (!success) {
          setError(t.authFailed);
          return;
        }
        onSuccess(email);
        onClose();
        return;
      }

      const success = await register(email, password, fullName);
      if (!success) {
        setError(t.authFailed);
        return;
      }
      onSuccess(email);
      onClose();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        t.authFailed
      );
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
      await api.post('/password/request', { email });
      setResetMessage(lang === 'ar' ? 'Sıfırlama bağlantısı e-posta gönderildi.' : 'Reset link sent to your email.');
    } catch (err) {
      setResetMessage(lang === 'ar' ? 'E-posta gönderilemedi. Tekrar deneyin.' : 'Failed to send reset email. Try again.');
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
            onClick={() => setActiveTab('login')}
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
            onClick={() => setActiveTab('register')}
            className={`rounded-md px-4 py-2 font-semibold ${
              activeTab === 'register'
                ? 'bg-purple-600 text-white'
                : 'text-slate-300 hover:text-white'
            }`}
          >
            {t.register}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
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
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={t.password}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white placeholder-slate-500"
            required
          />

          {activeTab === 'login' && (
            <div className="flex justify-end mt-2">
              <button
                type="button"
                onClick={requestReset}
                className="text-sm text-slate-300 hover:text-white underline"
                disabled={resetLoading}
              >
                {resetLoading ? (lang === 'ar' ? 'Gönderiliyor...' : 'Sending...') : (lang === 'ar' ? 'Şifremi Unuttum?' : 'Forgot password?')}
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
        </form>
      </div>
    </div>
  );
};

export default AuthModal;
