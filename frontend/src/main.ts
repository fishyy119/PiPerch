import './styles.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { createApp } from 'vue'

import { router } from '@/app/router'

import App from './App.vue'

createApp(App).use(createPinia()).use(VueQueryPlugin).use(router).mount('#app')
