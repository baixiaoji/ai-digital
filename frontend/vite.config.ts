import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: "127.0.0.1", // 明确使用 IPv4
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000", // 使用 IPv4 地址
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
});
