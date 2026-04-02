import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

// 路由配置
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' }
      },
      {
        path: 'assets',
        name: 'Assets',
        component: () => import('@/views/assets/AssetList.vue'),
        meta: { title: '资产管理', icon: 'Box' }
      },
      {
        path: 'assets/:id',
        name: 'AssetDetail',
        component: () => import('@/views/assets/AssetDetail.vue'),
        meta: { title: '资产详情', icon: 'Box' }
      },
      {
        path: 'assets/create',
        name: 'AssetCreate',
        component: () => import('@/views/assets/AssetForm.vue'),
        meta: { title: '创建资产', icon: 'Plus' }
      },
      {
        path: 'assets/:id/edit',
        name: 'AssetEdit',
        component: () => import('@/views/assets/AssetForm.vue'),
        meta: { title: '编辑资产', icon: 'Edit' }
      },
      {
        path: 'inspection',
        name: 'Inspection',
        component: () => import('@/views/inspection/InspectionIndex.vue'),
        meta: { title: '巡检管理', icon: 'Calendar' }
      },
      {
        path: 'inspection/plans',
        name: 'InspectionPlans',
        component: () => import('@/views/inspection/InspectionPlanList.vue'),
        meta: { title: '巡检计划', icon: 'Calendar' }
      },
      {
        path: 'inspection/records',
        name: 'InspectionRecords',
        component: () => import('@/views/inspection/InspectionRecordList.vue'),
        meta: { title: '巡检记录', icon: 'Document' }
      },
      {
        path: 'monitoring',
        name: 'Monitoring',
        component: () => import('@/views/monitoring/MonitoringIndex.vue'),
        meta: { title: '监控中心', icon: 'Monitor' }
      },
      {
        path: 'monitoring/alerts',
        name: 'Alerts',
        component: () => import('@/views/monitoring/AlertsPage.vue'),
        meta: { title: '告警中心', icon: 'Bell' }
      },
      {
        path: 'scheduler',
        name: 'Scheduler',
        component: () => import('@/views/scheduler/SchedulerIndex.vue'),
        meta: { title: '定时任务', icon: 'Timer' }
      },
      {
        path: 'monitor-test',
        name: 'MonitorTest',
        component: () => import('@/views/monitoring/MonitorTest.vue'),
        meta: { title: '采集测试', icon: 'Tools' }
      },
      {
        path: 'system',
        name: 'SystemSettings',
        component: () => import('@/views/system/SystemSettings.vue'),
        meta: { title: '系统设置', icon: 'Setting' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue')
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 运维管理系统` : '运维管理系统'
  
  // 检查是否需要登录
  if (to.meta.requiresAuth !== false) {
    const userStore = useUserStore()
    if (!userStore.isLoggedIn) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }
  
  next()
})

export default router