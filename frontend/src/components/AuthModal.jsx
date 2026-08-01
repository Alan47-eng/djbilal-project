import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import api from '../api';

const AuthModal = ({ isOpen, initialMode = 'login', onClose, onSuccess }) => {
  const [activeTab, setActiveTab] = useState(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    setActiveTab(initialMode);
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
        const response = await api.post('/login', { email, password });
        localStorage.setItem('accessToken', response.data.access_token);
        localStorage.setItem('userEmail', email);
        onSuccess(email);
        onClose();
        return;
      }

      await api.post('/register', { email, password });
      const loginResponse = await api.post('/login', { email, password });
      localStorage.setItem('accessToken', loginResponse.data.access_token);
      localStorage.setItem('userEmail', email);
      onSuccess(email);
      onClose();
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Authentication failed. Please try again.'
      );
    } finally {
      setLoading(false);
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
            {activeTab === 'login' ? 'Giriş Yap' : 'Kayıt Ol'}
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
            Login
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
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Email"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white placeholder-slate-500"
            required
          />
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-white placeholder-slate-500"
            required
          />

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
              ? 'Please wait...'
              : activeTab === 'login'
                ? 'Sign In'
                : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default AuthModal;
