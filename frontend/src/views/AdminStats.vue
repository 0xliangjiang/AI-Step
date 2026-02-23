<template>
  <div class="admin-stats">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <!-- 用户统计 -->
      <div class="stat-card">
        <div class="stat-icon users">👥</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.users?.total || 0 }}</div>
          <div class="stat-label">总用户数</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon bound">✅</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.users?.bound || 0 }}</div>
          <div class="stat-label">已绑定用户</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon today">🆕</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.users?.today_new || 0 }}</div>
          <div class="stat-label">今日新增用户</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon records">📋</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.records?.total || 0 }}</div>
          <div class="stat-label">总刷步记录</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon success">✓</div>
        <div class="stat-content">
          <div class="stat-value">{{ stats.records?.today_success || 0 }}</div>
          <div class="stat-label">今日成功刷步</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon steps">👟</div>
        <div class="stat-content">
          <div class="stat-value">{{ formatSteps(stats.steps?.today_total || 0) }}</div>
          <div class="stat-label">今日总步数</div>
        </div>
      </div>
    </div>

    <!-- 详细数据 -->
    <div class="detail-section">
      <div class="detail-card">
        <h3>用户状态分布</h3>
        <div class="progress-item">
          <div class="progress-label">
            <span>已绑定</span>
            <span>{{ stats.users?.bound || 0 }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill bound" :style="{ width: boundPercent + '%' }"></div>
          </div>
        </div>
        <div class="progress-item">
          <div class="progress-label">
            <span>未绑定</span>
            <span>{{ stats.users?.unbound || 0 }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill unbound" :style="{ width: unboundPercent + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="detail-card">
        <h3>刷步成功率</h3>
        <div class="progress-item">
          <div class="progress-label">
            <span>成功</span>
            <span>{{ stats.records?.success || 0 }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill success" :style="{ width: successPercent + '%' }"></div>
          </div>
        </div>
        <div class="progress-item">
          <div class="progress-label">
            <span>失败</span>
            <span>{{ stats.records?.failed || 0 }}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill failed" :style="{ width: (100 - successPercent) + '%' }"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminStats',
  data() {
    return {
      stats: {
        users: {},
        records: {},
        steps: {}
      }
    }
  },
  computed: {
    boundPercent() {
      const total = this.stats.users?.total || 0
      const bound = this.stats.users?.bound || 0
      return total > 0 ? Math.round((bound / total) * 100) : 0
    },
    unboundPercent() {
      return 100 - this.boundPercent
    },
    successPercent() {
      const total = this.stats.records?.total || 0
      const success = this.stats.records?.success || 0
      return total > 0 ? Math.round((success / total) * 100) : 0
    }
  },
  mounted() {
    this.loadStats()
    // 每30秒刷新一次
    this.timer = setInterval(this.loadStats, 30000)
  },
  beforeUnmount() {
    if (this.timer) {
      clearInterval(this.timer)
    }
  },
  methods: {
    async loadStats() {
      try {
        const res = await axios.get('/api/admin/stats')
        if (res.data.success) {
          this.stats = res.data.data
        }
      } catch (err) {
        console.error('加载统计失败:', err)
        if (err.response?.status === 401) {
          this.$router.push('/admin')
        }
      }
    },
    formatSteps(steps) {
      if (steps >= 10000) {
        return (steps / 10000).toFixed(1) + '万'
      }
      return steps.toLocaleString()
    }
  }
}
</script>

<style scoped>
.admin-stats {
  max-width: 1200px;
}

/* 统计卡片网格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: #1a1f2e;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-icon.users {
  background: rgba(74, 158, 255, 0.2);
}

.stat-icon.bound {
  background: rgba(16, 185, 129, 0.2);
}

.stat-icon.today {
  background: rgba(245, 158, 11, 0.2);
}

.stat-icon.records {
  background: rgba(139, 92, 246, 0.2);
}

.stat-icon.success {
  background: rgba(16, 185, 129, 0.2);
}

.stat-icon.steps {
  background: rgba(236, 72, 153, 0.2);
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.stat-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 4px;
}

/* 详细数据 */
.detail-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.detail-card {
  background: #1a1f2e;
  border-radius: 12px;
  padding: 20px;
}

.detail-card h3 {
  color: #fff;
  font-size: 16px;
  margin: 0 0 16px;
}

.progress-item {
  margin-bottom: 16px;
}

.progress-item:last-child {
  margin-bottom: 0;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  margin-bottom: 8px;
}

.progress-bar {
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-fill.bound {
  background: linear-gradient(90deg, #10b981, #34d399);
}

.progress-fill.unbound {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.progress-fill.success {
  background: linear-gradient(90deg, #10b981, #34d399);
}

.progress-fill.failed {
  background: linear-gradient(90deg, #ef4444, #f87171);
}
</style>
