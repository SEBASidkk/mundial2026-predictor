/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        'app-bg':      '#050A14',
        'app-surface': '#0D1829',
        'app-border':  '#1E3A5F',
        'app-primary': '#1E40AF',
        'app-blue':    '#3B82F6',
        'app-accent':  '#D97706',
        'app-amber':   '#F59E0B',
        'app-win':     '#22C55E',
        'app-draw':    '#94A3B8',
        'app-loss':    '#EF4444',
        'app-text':    '#F8FAFC',
        'app-muted':   '#94A3B8',
      },
      fontFamily: {
        mono: ['"Fira Code"', 'monospace'],
        sans: ['"Fira Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

