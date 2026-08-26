import axios from 'axios';

const AUTH_TOKEN_KEY = 'djbilal_auth_token';

export const getAuthToken = () => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
};

export const setAuthToken = (token) => {
  if (typeof window === 'undefined') return;
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    return;
  }
  localStorage.removeItem(AUTH_TOKEN_KEY);
};

const inferLocalBackendUrl = () => {
  if (typeof window === 'undefined') return 'http://localhost:8000';

  const hostname = window.location.hostname;
  const isPrivateHost =
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '0.0.0.0' ||
    /^192\.168\.\d{1,3}\.\d{1,3}$/.test(hostname) ||
    /^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(hostname) ||
    /^172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}$/.test(hostname);

  const protocol = isPrivateHost ? 'http:' : window.location.protocol;
  return `${protocol}//${hostname}:8000`;
};

const runtimeBaseUrl =
  typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.VITE_API_BASE_URL
    ? window.__ENV__.VITE_API_BASE_URL
    : null;

const rawBaseUrl = runtimeBaseUrl || import.meta.env.VITE_API_BASE_URL || inferLocalBackendUrl();
const apiBaseUrl = rawBaseUrl.replace(/\/+$/, '');

const api = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      setAuthToken(null);
    }
    return Promise.reject(error);
  }
);

export const resolveAssetUrl = (url) => {
  if (!url) return url;

  if (url.startsWith('/media/')) {
    return `${apiBaseUrl}${url}`;
  }

  try {
    const parsed = new URL(url);
    if (typeof window !== 'undefined' && window.location.protocol === 'https:' && parsed.protocol === 'http:') {
      parsed.protocol = 'https:';
    }
    return parsed.toString();
  } catch {
    return url;
  }
};

export default api;
