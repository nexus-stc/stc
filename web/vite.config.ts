import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import topLevelAwait from 'vite-plugin-top-level-await'
import wasm from 'vite-plugin-wasm'
import vuePugPlugin from 'vue-pug-plugin'

import summa_config from './summa-config.json'

// https://vitejs.dev/config/
export default defineConfig({
  base: '',
  build: {
    rollupOptions: {
      input: {
        index: './index.html'
      },
      output: [
        {
          name: 'assets/[name].[hash].js'
        }
      ]
    },
    target: 'esnext'
  },
  plugins: [
    react({
      include: '**/*.vue'
    }),
    vue({
      template: {
        preprocessOptions: {
          // 'preprocessOptions' is passed through to the pug compiler
          plugins: [vuePugPlugin]
        }
      }
    }),
    wasm(),
    topLevelAwait()
  ],
  worker: {
    format: 'es',
    plugins: [wasm()]
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '~': fileURLToPath(new URL('./node_modules', import.meta.url))
    },
    preserveSymlinks: true
  },
  server: {
    fs: {
      // Allow serving files from one level up to the project root
      allow: ['..']
    },
    proxy: {
      '/data': {
        target: `${summa_config.ipfs_http_base_url}/ipns/standard-template-construct.org`,
        changeOrigin: true,
        secure: false
      }
    }
  }
})
