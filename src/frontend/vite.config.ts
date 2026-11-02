import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// The backend has no CORS middleware, so dev requests go to a relative `/api`
// path and are proxied here. Override the upstream with BACKEND_URL.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.BACKEND_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})
