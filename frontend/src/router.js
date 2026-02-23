import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Chat from './views/Chat.vue'
import AdminLogin from './views/AdminLogin.vue'
import AdminLayout from './views/AdminLayout.vue'
import AdminUsers from './views/AdminUsers.vue'
import AdminRecords from './views/AdminRecords.vue'
import AdminStats from './views/AdminStats.vue'
import AdminConfig from './views/AdminConfig.vue'
import AdminTasks from './views/AdminTasks.vue'
import AdminCards from './views/AdminCards.vue'

const routes = [
  { path: '/', name: 'Login', component: Login },
  { path: '/chat', name: 'Chat', component: Chat },
  { path: '/admin', name: 'AdminLogin', component: AdminLogin },
  {
    path: '/admin/dashboard',
    component: AdminLayout,
    meta: { requiresAdminAuth: true },
    children: [
      { path: '', redirect: '/admin/dashboard/users' },
      { path: 'users', name: 'AdminUsers', component: AdminUsers },
      { path: 'records', name: 'AdminRecords', component: AdminRecords },
      { path: 'tasks', name: 'AdminTasks', component: AdminTasks },
      { path: 'cards', name: 'AdminCards', component: AdminCards },
      { path: 'stats', name: 'AdminStats', component: AdminStats },
      { path: 'config', name: 'AdminConfig', component: AdminConfig }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 用户端守卫
  const userKey = localStorage.getItem('userKey')
  if (to.name === 'Chat' && !userKey) {
    next({ name: 'Login' })
    return
  }

  // 管理端守卫
  const adminToken = localStorage.getItem('adminToken')
  if (to.meta.requiresAdminAuth && !adminToken) {
    next({ name: 'AdminLogin' })
    return
  }

  next()
})

export default router
