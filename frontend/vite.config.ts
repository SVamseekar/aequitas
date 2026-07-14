import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  envPrefix: ["VITE_", "NEXT_PUBLIC_"],
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, "index.html"),
        about: path.resolve(__dirname, "about.html"),
        contact: path.resolve(__dirname, "contact.html"),
        disclaimer: path.resolve(__dirname, "disclaimer.html"),
        privacy: path.resolve(__dirname, "privacy.html"),
        terms: path.resolve(__dirname, "terms.html"),
        refunds: path.resolve(__dirname, "refunds.html"),
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
