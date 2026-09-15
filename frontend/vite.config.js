import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Permite acceder desde túneles temporales (Cloudflare Tunnel,
    // ngrok...) cuyo dominio cambia cada vez que se arrancan.
    allowedHosts: true,
  },
})
