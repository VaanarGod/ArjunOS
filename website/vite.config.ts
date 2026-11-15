import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Change to '/your-repo-name/' for a GitHub Pages project site if needed.
// Using './' with HashRouter keeps assets and navigation stable.
export default defineConfig({
  plugins: [react()],
  base: './',
})
