/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        dt: {
          blue: '#1a6fff',
          dark: '#0a1628',
          darker: '#060e1e',
          card: '#0f1f3d',
          border: '#1e3a5f',
          text: '#c8d8f0',
        }
      }
    }
  },
  plugins: []
}
