import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: "../backend/app/dist-tmp", // временный выход
    assetsDir: "assets",
    emptyOutDir: true,
  },
  // для dev можно проксировать /api на Flask:
  server: {
    proxy: {
      "/api": "http://127.0.0.1:5001",
    },
  },
});
