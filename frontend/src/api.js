import axios from 'axios';

const runtimeBaseUrl =
  typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.VITE_API_BASE_URL
    ? window.__ENV__.VITE_API_BASE_URL
    : null;

const rawBaseUrl = runtimeBaseUrl || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const apiBaseUrl = rawBaseUrl.replace(/\/+$/, '');

// Create Axios instance with base URL pointing to backend
const api = axios.create({
  baseURL: apiBaseUrl,
});

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

// Interceptor: Add JWT token from localStorage to every request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor: Handle 401 responses (token expired/invalid)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login (could be handled by component)
      localStorage.removeItem('access_token');
      localStorage.removeItem('userEmail');
    }
    return Promise.reject(error);
  }
);

export default api;
