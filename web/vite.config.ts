/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env files (.env, .env.[mode], .env.local, ...) from the web/ dir.
  const env = loadEnv(mode, process.cwd(), '')
  // Backend that the dev server proxies "/api" to; overridable via env.
  const proxyTarget = env.VITE_DEV_PROXY_TARGET || 'http://localhost:8090'

  return {
    plugins: [
      vue(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
    server: {
      port: 4100,
      host: "localhost",
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'node',
      globals: false,
      include: ['src/**/*.spec.ts'],
    },
  }
})
