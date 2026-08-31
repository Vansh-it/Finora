import path from "path";
import { fileURLToPath } from "url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    port: 4321,
    proxy: {
      // Proxy /api requests to Flask backend
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      // Proxy /test page to Flask backend
      "/test": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
