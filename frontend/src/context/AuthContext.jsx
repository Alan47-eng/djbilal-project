import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { getAuthToken, setAuthToken } from '../api';
import { getApiErrorMessage } from '../utils/errors';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      setError(null);
      setLoading(false);
      return;
    }
    fetchUser();
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get('/me');
      setUser(response.data);
      setError(null);
      return { success: true, error: null };
    } catch (err) {
      setUser(null);
      let errorMessage = null;
      if (err.response?.status !== 401) {
        errorMessage = getApiErrorMessage(err, 'Failed to fetch user');
        setError(errorMessage);
      } else {
        setError(null);
      }
      setAuthToken(null);
      return { success: false, error: errorMessage || 'Authentication failed' };
    } finally {
      setLoading(false);
    }
  };

  const refreshUser = async () => {
    await fetchUser();
  };

  const login = async (email, password) => {
    try {
      const response = await api.post('/login', { email, password });
      const token = response.data?.access_token;
      if (token) {
        setAuthToken(token);
      }
      const userResult = await fetchUser();
      if (!userResult.success) {
        setAuthToken(null);
        return userResult;
      }
      setError(null);
      return userResult;
    } catch (err) {
      const errorMsg = getApiErrorMessage(err, 'Login failed');
      setError(errorMsg);
      setAuthToken(null);
      return { success: false, error: errorMsg };
    }
  };

  const register = async (email, password, fullName) => {
    try {
      await api.post('/register', {
        email,
        password,
        full_name: fullName?.trim() || null,
      });
      return await login(email, password);
    } catch (err) {
      const errorMsg = getApiErrorMessage(err, 'Registration failed');
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  };

  const logout = () => {
    api.post('/logout').catch(() => {});
    setAuthToken(null);
    setUser(null);
    setError(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
