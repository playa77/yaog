/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#0F1117',
          surface: '#161821',
          elevated: '#1C1F2B',
          hover: '#252836',
        },
        border: {
          DEFAULT: '#2A2D3A',
          light: '#363A4A',
        },
        text: {
          DEFAULT: '#C9CCD1',
          muted: '#6B6F7E',
          bright: '#EAECF0',
        },
        accent: {
          DEFAULT: '#D4A053',
          hover: '#E4B365',
          dim: 'rgba(212,160,83,0.12)',
          text: '#0F1117',
        },
        danger: {
          DEFAULT: '#E5484D',
          hover: '#F26669',
        },
      },
      fontFamily: {
        body: ['var(--font-chat)'],
        sans: ['var(--font-ui)'],
        mono: ['var(--font-mono)'],
      },
      fontSize: {
        chat: ['var(--size-chat)', { lineHeight: '1.78' }],
      },
      animation: {
        'breathe': 'breathe 2s ease-in-out infinite',
        'slide-in': 'slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        breathe: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.9' },
        },
        slideIn: {
          from: { transform: 'translateX(-100%)' },
          to: { transform: 'translateX(0)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
