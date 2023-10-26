import './scss/styles.scss'
import 'bootstrap'
import 'bootstrap/js/dist/tab'

import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import { get_label } from './translations'
import {SearchService} from "@/services/search/search-service";

// Set theme to the user's preferred color scheme
function updateTheme () {
  const color_mode = window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
  document.querySelector('html').setAttribute('data-bs-theme', color_mode)
}

// Set theme on load
updateTheme()

// Update theme when the preferred scheme changes
window
  .matchMedia('(prefers-color-scheme: dark)')
  .addEventListener('change', updateTheme)

const app = createApp(App)
app.use(router)

app.mixin({
  methods: {
    get_label
  }
})
app.config.globalProperties.search_service = new SearchService("info")
app.mount('#app')
