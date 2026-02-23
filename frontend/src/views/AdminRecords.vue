<template>
  <div class="admin-records">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <input
        v-model="userKey"
        type="text"
        placeholder="搜索用户标识..."
        @keyup.enter="search"
      />
      <select v-model="status">
        <option value="">全部状态</option>
        <option value="success">成功</option>
        <option value="failed">失败</option>
      </select>
      <button class="search-btn" @click="search">搜索</button>
    </div>

    <!-- 记录列表 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用户标识</th>
            <th>步数</th>
            <th>状态</th>
            <th>消息</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="6" class="loading-cell">加载中...</td>
          </tr>
          <tr v-else-if="records.length === 0">
            <td colspan="6" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-else v-for="record in records" :key="record.id">
            <td>{{ record.id }}</td>
            <td>{{ record.user_key }}</td>
            <td>{{ record.steps.toLocaleString() }}</td>
            <td>
              <span class="status-badge" :class="record.status">
                {{ record.status === 'success' ? '成功' : '失败' }}
              </span>
            </td>
            <td class="message-cell">{{ record.message || '-' }}</td>
            <td>{{ record.created_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页 (共 {{ total }} 条)</span>
      <button :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminRecords',
  data() {
    return {
      records: [],
      loading: false,
      userKey: '',
      status: '',
      page: 1,
      pageSize: 20,
      total: 0
    }
  },
  computed: {
    totalPages() {
      return Math.ceil(this.total / this.pageSize)
    }
  },
  mounted() {
    this.loadRecords()
  },
  methods: {
    async loadRecords() {
      this.loading = true
      try {
        const params = {
          page: this.page,
          page_size: this.pageSize,
          user_key: this.userKey || undefined,
          status: this.status || undefined
        }
        const res = await axios.get('/api/admin/step-records', { params })
        if (res.data.success) {
          this.records = res.data.data
          this.total = res.data.total
        }
      } catch (err) {
        console.error('加载记录失败:', err)
        if (err.response?.status === 401) {
          this.$router.push('/admin')
        }
      } finally {
        this.loading = false
      }
    },
    search() {
      this.page = 1
      this.loadRecords()
    },
    changePage(newPage) {
      this.page = newPage
      this.loadRecords()
    }
  }
}
</script>

<style scoped>
.admin-records {
  max-width: 1200px;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-bar input {
  flex: 1;
  padding: 10px 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 14px;
}

.search-bar input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.search-bar select {
  padding: 10px 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 14px;
}

.search-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #4a9eff 0%, #3b82f6 100%);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.table-container {
  background: #1a1f2e;
  border-radius: 12px;
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.data-table th {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: #fff;
  font-size: 14px;
}

.loading-cell,
.empty-cell {
  text-align: center;
  color: rgba(255, 255, 255, 0.5);
}

.message-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
}

.status-badge.success {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.status-badge.failed {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}

.pagination button {
  padding: 8px 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  background: transparent;
  color: #fff;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination span {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}
</style>
