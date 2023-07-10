import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
  base: "",
  build: {
    emptyOutDir: false,
    rollupOptions: {
      input: {
        "service-worker": "./node_modules/summa-wasm/dist/service-worker.js",
      },
      output: [
        {
          entryFileNames: () => {
            return "[name].js";
          },
        },
      ],
    },
    target: "esnext",
  },
});
