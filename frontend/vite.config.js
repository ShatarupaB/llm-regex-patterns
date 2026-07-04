import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    // Proxy API calls to Django so we never hit CORS issues in dev.
    // /api/* → http://web:8000/api/* (uses Docker service name)
    proxy: {
      '/api': {
        target: 'http://web:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://web:8000',
        changeOrigin: true,
      }
    }
  }
})
