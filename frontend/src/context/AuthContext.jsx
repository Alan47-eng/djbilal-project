import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { setAuthToken } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchUser();
  }, []);

  const fetchUser = async () => {
    try {
      const response = await api.get('/me');
      setUser(response.data);
      setError(null);
    } catch (err) {
      setUser(null);
      if (err.response?.status !== 401) {
        setError(err.response?.data?.detail || 'Failed to fetch user');
      } else {
        setError(null);
      }
      setAuthToken(null);
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
      await fetchUser();
      setError(null);
      return true;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Login failed';
      setError(errorMsg);
      setAuthToken(null);
      return false;
    }
  };

  const register = async (email, password, fullName) => {
    try {
      await api.post('/register', {
        email,
        password,
        full_name: fullName?.trim() || null,
      });
      await login(email, password);
      return true;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Registration failed';
      setError(errorMsg);
      return false;
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
