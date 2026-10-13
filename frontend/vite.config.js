import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Fixed zone so the datetime tests (incl. the DST gap) behave the same everywhere.
process.env.TZ = 'America/New_York';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.js'],
    env: { VITE_API_URL: 'http://localhost:8000/api/v1' },
  },
});
