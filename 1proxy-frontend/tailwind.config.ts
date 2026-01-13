import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        retro: {
          pink: "#FF69B4",
          yellow: "#FFD93D",
          blue: "#6BCB77",
          purple: "#A29BFE",
          orange: "#FF6B6B",
          red: "#FF5252",
        },
        dark: {
          bg: "#1a1a2e",
          card: "#2d2d3a",
          border: "#3a3a4a",
          text: "#e4e4e7",
        },
        light: {
          bg: "#fef9f0",
          card: "#ffffff",
          border: "#000000",
          text: "#1a1a1a",
        },
      },
      fontFamily: {
        retro: ["'Bangers'", "'Comic Neue MS'", "cursive"],
        body: ["'Press Start 2P'", "'Courier New'", "monospace"],
      },
      boxShadow: {
        retro: "4px 4px 0px #000000",
        retroHard: "6px 6px 0px #000000",
      },
      borderWidth: {
        retro: "3px",
      },
      borderRadius: {
        retro: "8px",
      },
    },
  },
  plugins: [],
};
export default config;
