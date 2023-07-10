import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import topLevelAwait from "vite-plugin-top-level-await";
import vue from "@vitejs/plugin-vue";
import vuePugPlugin from "vue-pug-plugin";
import wasm from "vite-plugin-wasm";

// https://vitejs.dev/config/
export default defineConfig({
  base: "",
  build: {
    rollupOptions: {
      input: {
        index: "./index.html",
      },
      output: [
        {
          name: "assets/[name].[hash].js",
        },
      ],
    },
    target: "esnext",
  },
  plugins: [
    vue({
      template: {
        preprocessOptions: {
          // 'preprocessOptions' is passed through to the pug compiler
          plugins: [vuePugPlugin],
        },
      },
    }),
    wasm(),
    topLevelAwait(),
  ],
  worker: {
    format: "es",
    plugins: [wasm()],
  },
  optimizeDeps: {
    esbuildOptions: {
      target: "es2022",
    },
    include: [
      "@libp2p/logger",
      "@multiformats/multiaddr",
      "dexie",
      "ipfs-core-types",
      "ipfs-http-client",
      "merge-options",
      "summa-wasm",
    ],
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "~": fileURLToPath(new URL("./node_modules", import.meta.url)),
    },
    preserveSymlinks: true,
  },
  server: {
    fs: {
      // Allow serving files from one level up to the project root
      allow: [".."],
    },
  },
});
