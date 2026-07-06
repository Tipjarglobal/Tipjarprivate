/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      fontFamily: {
        heading: ["Outfit", "sans-serif"],
        body: ["Manrope", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        void: "#09090B",
        surface: "#18181B",
        elevated: "#27272A",
        volt: "#E1FF00",
        "volt-hover": "#CCEE00",
        bell: "#FF1E56",
        won: "#00FF94",
        lost: "#FF1E56",
        border: "#27272A",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        "bell-ring": {
          "0%,100%": { transform: "rotate(0)" },
          "10%,30%": { transform: "rotate(14deg)" },
          "20%,40%": { transform: "rotate(-14deg)" },
        },
        "pulse-glow": {
          "0%,100%": { boxShadow: "0 0 0 0 rgba(255,30,86,0.5)" },
          "50%": { boxShadow: "0 0 0 10px rgba(255,30,86,0)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "bell-ring": "bell-ring 1s ease-in-out",
        "pulse-glow": "pulse-glow 2s infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
