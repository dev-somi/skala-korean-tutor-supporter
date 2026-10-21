import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// 브라우저는 backend(Spring)만 호출한다 (ADR-0006). 개발 중에는 Vite가 /api를 8080으로 넘긴다 → CORS 불필요.
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8080', changeOrigin: true },
    },
  },
})
