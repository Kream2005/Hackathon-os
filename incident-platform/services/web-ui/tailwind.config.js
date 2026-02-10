/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: 'hsl(220 13% 20%)',
        background: 'hsl(220 16% 6%)',
        foreground: 'hsl(210 20% 95%)',
        card: 'hsl(220 15% 9%)',
        'card-foreground': 'hsl(210 20% 95%)',
        muted: 'hsl(220 14% 14%)',
        'muted-foreground': 'hsl(215 15% 55%)',
        primary: 'hsl(221 83% 53%)',
        'primary-foreground': 'hsl(0 0% 100%)',
        secondary: 'hsl(220 14% 14%)',
        'secondary-foreground': 'hsl(210 20% 85%)',
        destructive: 'hsl(0 84% 60%)',
        'destructive-foreground': 'hsl(0 0% 100%)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
