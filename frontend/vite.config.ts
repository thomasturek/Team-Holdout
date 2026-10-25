import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'node:path';
import { runsApi } from './server/runs';

export default defineConfig({
  plugins: [vue(), runsApi(process.env.RUNS_DIR || path.resolve(__dirname, '../runs'))],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
  },
});
