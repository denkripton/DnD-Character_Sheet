import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  root: new URL('..', import.meta.url).pathname,
  plugins: [react()],
  resolve: {
    alias: {
      react: new URL('./node_modules/react', import.meta.url).pathname,
      'react-dom': new URL('./node_modules/react-dom', import.meta.url).pathname,
      'react-router-dom': new URL('./node_modules/react-router-dom', import.meta.url).pathname,
      vitest: new URL('./node_modules/vitest', import.meta.url).pathname,
    },
  },
  test: { environment: 'node' },
})
