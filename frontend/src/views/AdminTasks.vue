<template>
  <div class="admin-page">
    <div class="page-header">
      <h2>定时任务管理</h2>
      <p>管理用户的定时刷步任务</p>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <select v-model="filterStatus" @change="loadTasks">
        <option value="">全部状态</option>
        <option value="active">执行中</option>
        <option value="paused">已暂停</option>
        <option value="cancelled">已取消</option>
      </select>
      <button class="btn-refresh" @click="loadTasks">
        <span>刷新</span>
      </button>
    </div>

    <!-- 任务列表 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>用户标识</th>
            <th>目标步数</th>
            <th>时间段</th>
            <th>当前进度</th>
            <th>状态</th>
            <th>上次执行</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id">
            <td>
              <div class="user-info">
                <span class="user-key">{{ task.user_key }}</span>
                <span class="user-email" v-if="task.user_email">{{ task.user_email }}</span>
              </div>
            </td>
            <td>{{ task.target_steps.toLocaleString() }} 步</td>
            <td>{{ task.start_hour }}:00 - {{ task.end_hour }}:00</td>
            <td>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: getProgress(task) + '%' }"></div>
              </div>
              <span class="progress-text">{{ task.current_steps.toLocaleString() }} / {{ task.target_steps.toLocaleString() }}</span>
            </td>
            <td>
              <span :class="['status-badge', task.status]">
                {{ getStatusText(task.status) }}
              </span>
            </td>
            <td>{{ task.last_run_at || '-' }}</td>
            <td>
              <div class="action-btns">
                <button v-if="task.status === 'active'" class="btn-small btn-warning" @click="pauseTask(task)">
                  暂停
                </button>
                <button v-if="task.status === 'paused'" class="btn-small btn-success" @click="resumeTask(task)">
                  恢复
                </button>
                <button v-if="task.status !== 'cancelled'" class="btn-small btn-danger" @click="cancelTask(task)">
                  取消
                </button>
                <button class="btn-small btn-danger" @click="deleteTask(task)">
                  删除
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="tasks.length === 0">
            <td colspan="7" class="empty-text">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 统计 -->
    <div class="stats-bar" v-if="tasks.length > 0">
      <span>共 {{ tasks.length }} 个任务</span>
      <span>执行中: {{ tasks.filter(t => t.status === 'active').length }}</span>
      <span>已暂停: {{ tasks.filter(t => t.status === 'paused').length }}</span>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminTasks',
  data() {
    return {
      tasks: [],
      filterStatus: ''
    }
  },
  mounted() {
    this.loadTasks()
  },
  methods: {
    async loadTasks() {
      try {
        const token = localStorage.getItem('adminToken')
        const res = await axios.get('/api/admin/scheduled-tasks', {
          params: { status: this.filterStatus },
          headers: { Authorization: `Bearer ${token}` }
        })
        this.tasks = res.data.data || []
      } catch (error) {
        console.error('加载任务失败:', error)
      }
    },

    getProgress(task) {
      if (!task.target_steps) return 0
      return Math.min(100, Math.round((task.current_steps / task.target_steps) * 100))
    },

    getStatusText(status) {
      const map = {
        'active': '执行中',
        'paused': '已暂停',
        'cancelled': '已取消'
      }
      return map[status] || status
    },

    async pauseTask(task) {
      if (!confirm('确定暂停该任务？')) return
      try {
        const token = localStorage.getItem('adminToken')
        await axios.post(`/api/admin/scheduled-tasks/${task.id}/pause`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.loadTasks()
      } catch (error) {
        alert('操作失败')
      }
    },

    async resumeTask(task) {
      try {
        const token = localStorage.getItem('adminToken')
        await axios.post(`/api/admin/scheduled-tasks/${task.id}/resume`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.loadTasks()
      } catch (error) {
        alert('操作失败')
      }
    },

    async cancelTask(task) {
      if (!confirm('确定取消该任务？')) return
      try {
        const token = localStorage.getItem('adminToken')
        await axios.post(`/api/admin/scheduled-tasks/${task.id}/cancel`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.loadTasks()
      } catch (error) {
        alert('操作失败')
      }
    },

    async deleteTask(task) {
      if (!confirm('确定删除该任务？此操作不可恢复。')) return
      try {
        const token = localStorage.getItem('adminToken')
        await axios.delete(`/api/admin/scheduled-tasks/${task.id}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.loadTasks()
      } catch (error) {
        alert('操作失败')
      }
    }
  }
}
</script>

<style scoped>
.admin-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 8px;
}

.page-header p {
  color: #8899a6;
  font-size: 14px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.filter-bar select {
  padding: 10px 16px;
  border: 1px solid #38444d;
  border-radius: 8px;
  background: #192734;
  color: #fff;
  font-size: 14px;
}

.btn-refresh {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #1da1f2;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-refresh:hover {
  background: #1a91da;
}

.table-container {
  background: #192734;
  border-radius: 12px;
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 16px;
  text-align: left;
  font-weight: 600;
  color: #8899a6;
  font-size: 13px;
  text-transform: uppercase;
  border-bottom: 1px solid #38444d;
}

.data-table td {
  padding: 16px;
  color: #fff;
  border-bottom: 1px solid #38444d;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-key {
  font-weight: 500;
}

.user-email {
  font-size: 12px;
  color: #8899a6;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: #38444d;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1da1f2, #17bf63);
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  color: #8899a6;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.active {
  background: rgba(23, 191, 99, 0.2);
  color: #17bf63;
}

.status-badge.paused {
  background: rgba(255, 173, 31, 0.2);
  color: #ffad1f;
}

.status-badge.cancelled {
  background: rgba(224, 36, 94, 0.2);
  color: #e0245e;
}

.action-btns {
  display: flex;
  gap: 8px;
}

.btn-small {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-small:hover {
  opacity: 0.8;
}

.btn-success {
  background: #17bf63;
  color: #fff;
}

.btn-warning {
  background: #ffad1f;
  color: #000;
}

.btn-danger {
  background: #e0245e;
  color: #fff;
}

.empty-text {
  text-align: center;
  color: #8899a6;
  padding: 40px !important;
}

.stats-bar {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  font-size: 14px;
  color: #8899a6;
}
</style>
