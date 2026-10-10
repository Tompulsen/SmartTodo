import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import axios from 'axios'
import { detectLocalMode } from './local-mode'
import { auth, loadSession } from './auth'
import { getCsrfToken } from './http'

// fontAwesome相关配置
import { library } from '@fortawesome/fontawesome-svg-core'
import {
  faTrashAlt,
  faClock,
  faCheck,
  faUndo,
  faAngleDoubleDown,
  faAngleDoubleUp,
  faCalculator
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
library.add(faTrashAlt, faClock, faCheck, faUndo, faAngleDoubleDown, faAngleDoubleUp, faCalculator)

// axios相关配置
axios.defaults.baseURL = '/api'
axios.interceptors.request.use((config) => {
  if (!['get', 'head', 'options'].includes((config.method || 'get').toLowerCase())) {
    config.headers.set('X-CSRF-Token', getCsrfToken())
  }
  return config
})

function requireLogin() {
  if (auth.localMode || ['/login', '/register'].includes(router.currentRoute.value.path)) return
  auth.user = null
  void router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
}
window.addEventListener('auth-required', requireLogin)

axios.interceptors.response.use(
  (res) => {
    return res
  },
  (error) => {
    if (error.response?.status === 401) requireLogin()
    return Promise.reject(error)
  }
)

async function mountApp() {
  await detectLocalMode()
  await loadSession()

  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.component('font-awesome-icon', FontAwesomeIcon)
  app.mount('#app')
}

void mountApp()
