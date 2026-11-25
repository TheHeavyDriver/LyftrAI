import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
    host: '0.0.0.0',
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  define: {
    'process.env.VITE_API_BASE_URL': JSON.stringify(
      process.env.VITE_API_BASE_URL || 'http://localhost:8000'
    ),
  },
});
