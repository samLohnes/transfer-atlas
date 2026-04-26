import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Default to localhost so `npm run dev` works on the host. Inside docker-compose
// the web service sets VITE_API_PROXY_TARGET=http://api:8000 so the container
// uses docker's internal DNS to reach the api service.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
