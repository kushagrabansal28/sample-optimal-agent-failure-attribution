/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000', '/files': 'http://localhost:8000' } },
  preview: { port: 4173, proxy: { '/api': 'http://localhost:8000', '/files': 'http://localhost:8000' } },   // `npm run preview` talks to the API too
  build: { chunkSizeWarningLimit: 900 },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], css: false },
})
