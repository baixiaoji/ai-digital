/** @type {import('tailwindcss').Config} */
import typography from '@tailwindcss/typography'

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/streamdown/dist/*.js"
  ],
  theme: {
    extend: {},
  },
  plugins: [typography],
}
