import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/hooks/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        border: "hsl(var(--border))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))"
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))"
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))"
        },
        ring: "hsl(var(--ring))"
      },
      fontFamily: {
        body: ["var(--font-body)"],
        display: ["var(--font-display)"]
      },
      boxShadow: {
        glow: "0 24px 60px rgba(15, 23, 42, 0.16)",
        card: "0 18px 45px rgba(15, 23, 42, 0.08)"
      },
      backgroundImage: {
        "grid-pattern":
          "linear-gradient(to right, rgba(148, 163, 184, 0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(148, 163, 184, 0.08) 1px, transparent 1px)"
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-14px)" }
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" }
        },
        pulseLine: {
          "0%, 100%": { opacity: "0.5", transform: "scaleX(0.92)" },
          "50%": { opacity: "1", transform: "scaleX(1)" }
        }
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        shimmer: "shimmer 7s linear infinite",
        pulseLine: "pulseLine 3.6s ease-in-out infinite"
      }
    }
  },
  plugins: []
};

export default config;
