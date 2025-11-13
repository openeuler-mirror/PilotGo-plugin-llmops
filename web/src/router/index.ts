import { createRouter, createWebHistory } from 'vue-router'
import Overview from '../views/Overview.vue'
import Project from '../views/Project.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Overview',
      component: Overview
    },
    {
      path: '/project/:id',
      name: 'Project',
      component: Project,
      props: true
    }
  ],
})

export default router
