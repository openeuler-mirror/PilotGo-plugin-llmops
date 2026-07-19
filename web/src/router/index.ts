import { createRouter, createWebHistory } from 'vue-router'
import Overview from '../views/Overview.vue'
import Project from '../views/Project.vue'
import ClusterView from '../views/ClusterView.vue'
import AgentView from '../views/AgentView.vue'
import McpView from '../views/McpView.vue'
import SkillView from '../views/SkillView.vue'
import KnowledgeBase from '../views/KnowledgeBase.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/overview'
    },
    {
      path: '/overview',
      name: 'Overview',
      component: Overview
    },
    {
      path: '/project/:id',
      name: 'Project',
      component: Project,
      props: true
    },
    {
      path: '/cluster',
      name: 'Cluster',
      component: ClusterView
    },
    {
      path: '/agent',
      name: 'Agent',
      component: AgentView
    },
    {
      path: '/mcp',
      name: 'Mcp',
      component: McpView
    },
    {
      path: '/skill',
      name: 'Skill',
      component: SkillView
    },
    {
      path: '/knowledge',
      name: 'KnowledgeBase',
      component: KnowledgeBase
    }
  ],
})

export default router
