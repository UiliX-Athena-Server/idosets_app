import { defineConfig } from 'vite'
import solid from '@solidjs/vite-plugin'
import tailwindcss from '@tailwindcss/vite'

const FLASK = process.env.FLASK_URL || 'http://127.0.0.1:5001'

export default defineConfig({
  plugins: [solid(), tailwindcss()],
  root: '.',
  server: {
    host: '127.0.0.1',
    port: 5002,
    // Same-origin API calls in development: no CORS, cookies just work.
    proxy: {
      '/api': { target: FLASK, changeOrigin: false },
      '/--vite--': { target: FLASK, changeOrigin: false },
    },
  },
  build: {
    // flask-vite-transporter injects every built .js file as a script tag,
    // so keep the build to a single bundle.
    rolldownOptions: { output: { codeSplitting: false } },
  },
})
