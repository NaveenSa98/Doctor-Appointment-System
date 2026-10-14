import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Fixed zone so the datetime tests (incl. the DST gap) behave the same everywhere.
process.env.TZ = 'America/New_York';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 127.0.0.1, not "localhost": on Windows localhost can resolve to IPv6 (::1), where uvicorn
    // is not listening.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.js'],
    env: { VITE_API_URL: 'http://localhost:8000/api/v1' },
  },
});
