import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: { ink: "#14211b", cream: "#f5f3ec", moss: "#325b48", mint: "#dce9e1", amber: "#d88b2d" },
      boxShadow: { card: "0 1px 2px rgba(20,33,27,.05), 0 12px 32px rgba(20,33,27,.06)" },
    },
  },
  plugins: [],
} satisfies Config;
