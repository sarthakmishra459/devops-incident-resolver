import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172026",
        panel: "#f7f8f3",
        line: "#d8ded2",
        signal: "#0f766e",
        alert: "#be123c",
        amber: "#b45309"
      },
      boxShadow: {
        soft: "0 18px 60px rgba(23, 32, 38, 0.12)"
      }
    }
  },
  plugins: []
} satisfies Config;
