import axios from 'axios';

const runtimeBaseUrl =
  typeof window !== 'undefined' && window.__ENV__ && window.__ENV__.VITE_API_BASE_URL
    ? window.__ENV__.VITE_API_BASE_URL
    : null;

// Create Axios instance with base URL pointing to backend
const api = axios.create({
  baseURL: runtimeBaseUrl || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

// Interceptor: Add JWT token from localStorage to every request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
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
      localStorage.removeItem('accessToken');
      localStorage.removeItem('userEmail');
    }
    return Promise.reject(error);
  }
);

export default api;
