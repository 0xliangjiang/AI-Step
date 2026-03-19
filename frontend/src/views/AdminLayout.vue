<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>AI智能刷步</h2>
        <span>管理后台</span>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/admin/dashboard/users" class="nav-item" :class="{ active: $route.path.includes('/users') }">
          <span class="icon">👥</span>
          <span>用户管理</span>
        </router-link>
        <router-link to="/admin/dashboard/tasks" class="nav-item" :class="{ active: $route.path.includes('/tasks') }">
          <span class="icon">⏰</span>
          <span>定时任务</span>
        </router-link>
        <router-link to="/admin/dashboard/cards" class="nav-item" :class="{ active: $route.path.includes('/cards') }">
          <span class="icon">🎫</span>
          <span>卡密管理</span>
        </router-link>
        <router-link to="/admin/dashboard/packages" class="nav-item" :class="{ active: $route.path.includes('/packages') }">
          <span class="icon">💎</span>
          <span>VIP套餐</span>
        </router-link>
        <router-link to="/admin/dashboard/records" class="nav-item" :class="{ active: $route.path.includes('/records') }">
          <span class="icon">📋</span>
          <span>刷步记录</span>
        </router-link>
        <router-link to="/admin/dashboard/stats" class="nav-item" :class="{ active: $route.path.includes('/stats') }">
          <span class="icon">📊</span>
          <span>数据统计</span>
        </router-link>
        <router-link to="/admin/dashboard/config" class="nav-item" :class="{ active: $route.path.includes('/config') }">
          <span class="icon">⚙️</span>
          <span>系统配置</span>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <button class="logout-btn" @click="logout">退出登录</button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <header class="main-header">
        <h1>{{ pageTitle }}</h1>
        <div class="header-actions">
          <span class="time">{{ currentTime }}</span>
        </div>
      </header>
      <div class="main-body">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminLayout',
  data() {
    return {
      currentTime: ''
    }
  },
  computed: {
    pageTitle() {
      const titles = {
        '/admin/dashboard/users': '用户管理',
        '/admin/dashboard/tasks': '定时任务',
        '/admin/dashboard/cards': '卡密管理',
        '/admin/dashboard/packages': 'VIP套餐',
        '/admin/dashboard/records': '刷步记录',
        '/admin/dashboard/stats': '数据统计',
        '/admin/dashboard/config': '系统配置'
      }
      return titles[this.$route.path] || '管理后台'
    }
  },
  mounted() {
    this.updateTime()
    setInterval(this.updateTime, 1000)
    this.setupAxios()
  },
  methods: {
    updateTime() {
      const now = new Date()
      this.currentTime = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    },
    setupAxios() {
      const token = localStorage.getItem('adminToken')
      if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      }
    },
    logout() {
      localStorage.removeItem('adminToken')
      delete axios.defaults.headers.common['Authorization']
      this.$router.push('/admin')
    }
  }
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #0f1419;
}

/* 侧边栏 */
.sidebar {
  width: 240px;
  background: #1a1f2e;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar-header h2 {
  color: #fff;
  font-size: 20px;
  margin: 0 0 4px;
}

.sidebar-header span {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  border-radius: 8px;
  margin-bottom: 4px;
  transition: all 0.2s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
}

.nav-item.active {
  background: linear-gradient(135deg, #4a9eff 0%, #3b82f6 100%);
  color: #fff;
}

.nav-item .icon {
  font-size: 18px;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.logout-btn {
  width: 100%;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

/* 主内容区 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.main-header {
  padding: 20px 24px;
  background: #1a1f2e;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.main-header h1 {
  color: #fff;
  font-size: 20px;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.time {
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
}

.main-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>
