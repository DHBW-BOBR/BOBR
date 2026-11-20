import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import ImportView from './views/ImportView.vue'
import ResultsView from './views/ResultsView.vue'
import UploadsView from './views/UploadsView.vue'
import UploadDetailView from './views/UploadDetailView.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ImportView },
    { path: '/results', component: ResultsView },
    // Gespeicherte Prüfungen: Übersicht und Detailseite einer Prüfung
    { path: '/uploads', component: UploadsView },
    { path: '/uploads/:id', component: UploadDetailView },
  ],
})

createApp(App).use(router).mount('#app')
