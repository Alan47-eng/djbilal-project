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
  withCredentials: true,
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

api.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
);

export default api;
