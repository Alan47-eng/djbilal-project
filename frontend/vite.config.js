import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    allowedHosts: ['djbilal-frontend-production.up.railway.app', 'localhost', '127.0.0.1'],
  },
});