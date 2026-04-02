/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#FF6B00',
          dark: '#CC5500',
          light: '#FF8C3A',
        },
        surface: {
          DEFAULT: '#0F0F13',
          2: '#16161C',
          3: '#1E1E27',
          4: '#252530',
          border: '#2A2A38',
        }
      },
      fontFamily: {
        sans: ['Rajdhani', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Barlow Condensed', 'sans-serif'],
      }
    }
  },
  plugins: []
}
