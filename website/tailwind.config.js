/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        void: '#000000',        // Pure black
        midnight: '#050505',    // Deep charcoal
        navy: '#0a0a0a',        // Dark grey surface
        cyan: '#22d3ee',
        ice: '#a5f3fc',
        violet: '#8b5cf6',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 40px rgba(34, 211, 238, 0.15)',
        'glow-strong': '0 0 80px rgba(34, 211, 238, 0.3)',
        'glass': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
      },
      animation: {
        'pulse-slow': 'pulse 6s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 8s ease-in-out infinite',
        'spin-slow': 'spin 30s linear infinite',
        'soundwave': 'soundwave 1.2s ease-in-out infinite',
        'data-flow': 'dataFlow 3s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        soundwave: {
          '0%, 100%': { transform: 'scaleY(0.3)' },
          '50%': { transform: 'scaleY(1)' },
        },
        dataFlow: {
          '0%': { strokeDashoffset: '24' },
          '100%': { strokeDashoffset: '0' },
        }
      },
    },
  },
  plugins: [],
}
