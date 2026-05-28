/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      backgroundImage: {
        "gradient-brand": "linear-gradient(135deg, #6366f1, #8b5cf6)",
        "gradient-brand-r": "linear-gradient(to right, #6366f1, #8b5cf6)",
        "gradient-brand-45": "linear-gradient(45deg, #6366f1, #8b5cf6)",
      },
      boxShadow: {
        "glow-sm": "0 0 14px rgba(99,102,241,0.3)",
        "glow": "0 0 24px rgba(99,102,241,0.35), 0 0 48px rgba(99,102,241,0.15)",
        "glow-lg": "0 0 40px rgba(99,102,241,0.4), 0 0 80px rgba(139,92,246,0.2)",
        "card-dark": "0 1px 1px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.04)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Syne", "Inter", "ui-sans-serif", "sans-serif"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
