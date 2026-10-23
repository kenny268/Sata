/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f3f5f8",
        ink: "#142033",
        mute: "#5c6b80",
        line: "#e3e8ef",
      },
      fontFamily: {
        sans: ['"Avenir Next"', "Segoe UI", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
