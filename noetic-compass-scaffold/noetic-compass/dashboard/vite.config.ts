import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/') || id.includes('node_modules/react-router')) return 'vendor'
          if (id.includes('node_modules/@tanstack')) return 'query'
          if (id.includes('node_modules/recharts') || id.includes('node_modules/d3-')) return 'recharts'
          if (id.includes('node_modules/jspdf') || id.includes('node_modules/html2canvas')) return 'export-pdf'
          if (id.includes('node_modules/docx') || id.includes('node_modules/file-saver')) return 'export-docx'
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
})
