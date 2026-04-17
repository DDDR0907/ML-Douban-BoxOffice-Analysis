import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '数据概览' }
  },
  {
    path: '/data',
    name: 'DataManage',
    component: () => import('@/views/DataManage.vue'),
    meta: { title: '数据管理' }
  },
  {
    path: '/model',
    name: 'ModelTrain',
    component: () => import('@/views/ModelTrain.vue'),
    meta: { title: '模型训练' }
  },
  {
    path: '/predict',
    name: 'Predict',
    component: () => import('@/views/Predict.vue'),
    meta: { title: '票房预测' }
  },
  {
    path: '/visualize',
    name: 'Visualize',
    component: () => import('@/views/Visualize.vue'),
    meta: { title: '数据可视化' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title} - 豆瓣电影票房预测系统`
  next()
})

export default router
