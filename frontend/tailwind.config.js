/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        dt: {
          // Dynatrace (Strato-style) dark palette
          blue: '#1496ff',
          'blue-hover': '#0d7fe0',
          purple: '#6f2da8',
          lime: '#b4dc00',
          dark: '#14151f',
          darker: '#0e0f17',
          card: '#1c1d2b',
          border: '#33354a',
          text: '#d9dbe8',
        }
      }
    }
  },
  plugins: []
}
