import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, Vite forwards /api calls to the Flask backend,
// so the browser only ever talks to one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:5000",
    },
  },
});
