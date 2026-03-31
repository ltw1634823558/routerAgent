import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/model',
  },
  {
    path: '/model',
    name: 'ModelConfig',
    component: () => import('@/views/ModelConfig.vue'),
    meta: { title: '模型配置' },
  },
  {
    path: '/search',
    name: 'SearchAgent',
    component: () => import('@/views/SearchAgent.vue'),
    meta: { title: '搜集 Agent' },
  },
  {
    path: '/prompt',
    name: 'PromptAgent',
    component: () => import('@/views/PromptAgent.vue'),
    meta: { title: '提示词优化' },
  },
  {
    path: '/quiz',
    name: 'QuizAgent',
    component: () => import('@/views/QuizAgent.vue'),
    meta: { title: '问答 Agent' },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/Knowledge.vue'),
    meta: { title: '知识库' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || ''} - RouterAgent`
  next()
})

export default router
