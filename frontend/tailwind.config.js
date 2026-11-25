/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'warm-bg': '#fdfcfb',
        'warm-surface': '#f8f7f5',
        'ink': '#1a1818',
        'ink-muted': '#5a5555',
        'signal-green': '#10b981',
        'signal-amber': '#f59e0b',
        'border-subtle': '#e5e3e0',
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
