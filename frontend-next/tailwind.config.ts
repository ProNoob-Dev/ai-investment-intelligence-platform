import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#f7f9fa",
        surface: "#ecf0f2",
        ink: "#1f3038",
        muted: "#4a565e", /* 7.1:1 on paper; the dealt #5d6b72 was 5.2:1 */
        accent: "#0d7480",
        "accent-ink": "#ffffff",
        inv: { bg: "#1f3038", surface: "#2c3c44", ink: "#f7f9fa", muted: "#b3bcc0" }, /* 7.1:1 on ink */
        buy: "#0d7480",
        sell: "#c2402a",
        hold: "#8a6d00",
      },
      fontFamily: {
        display: ['"Geist"', "system-ui", "sans-serif"],
        text: ['"Geist"', "system-ui", "sans-serif"],
        mono: ['"Geist Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        // sharp radius for fintech: no rounded cards, 2px at most.
        none: "0px",
        sm: "2px",
        DEFAULT: "2px",
        md: "2px",
        lg: "2px",
        xl: "2px",
        full: "9999px",
      },
    },
  },
  plugins: [],
};

export default config;
