import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/app/',
  server: {
    proxy: {
      '/tree': 'http://localhost:8000',
      '/card': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
