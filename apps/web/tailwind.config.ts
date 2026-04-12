import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#060a12",
          panel: "#0e1524",
          border: "#1d2a44",
          text: "#d7e3ff",
          accent: "#5ec8ff"
        }
      }
    }
  },
  plugins: []
};

export default config;
