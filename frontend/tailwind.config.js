module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["IBM Plex Sans", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      colors: {
        app: "#050505",
        panel: "#0a0a0a",
        surface: "#141414",
        hoverbg: "#1f1f22",
      },
    },
  },
  plugins: [],
};
