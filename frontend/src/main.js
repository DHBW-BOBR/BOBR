import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import ImportView from './views/ImportView.vue'
import ResultsView from './views/ResultsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ImportView },
    { path: '/results', component: ResultsView },
  ],
})

createApp(App).use(router).mount('#app')
