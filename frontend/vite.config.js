// Stub created in Phase 1 (scaffold). Finalised in Phase 3 per
// IMPLEMENTATION.md §Phase 3 — React plugin, /api dev proxy to :8000,
// build outDir 'dist'.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 127.0.0.1, not localhost: Node 18 resolves localhost to IPv6 ::1 first,
      // but uvicorn binds IPv4 by default -> ECONNREFUSED ::1:8000.
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
