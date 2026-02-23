<template>
  <div class="admin-users">
    <!-- 操作栏 -->
    <div class="action-bar">
      <div class="search-bar">
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索用户标识/邮箱..."
          @keyup.enter="search"
        />
        <select v-model="bindStatus">
          <option value="">全部状态</option>
          <option value="0">未绑定</option>
          <option value="1">已绑定</option>
        </select>
        <button class="search-btn" @click="search">搜索</button>
      </div>
      <button class="batch-btn" @click="showBatchModal = true">
        <span class="btn-icon">+</span>
        批量注册账户
      </button>
    </div>

    <!-- 用户列表 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>用户标识</th>
            <th>Zepp 邮箱</th>
            <th>绑定状态</th>
            <th>注册时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="loading-cell">加载中...</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="5" class="empty-cell">暂无数据</td>
          </tr>
          <tr v-else v-for="user in users" :key="user.id">
            <td>{{ user.user_key }}</td>
            <td>{{ user.zepp_email || '-' }}</td>
            <td>
              <span class="status-badge" :class="user.bind_status === 1 ? 'bound' : 'unbound'">
                {{ user.bind_status === 1 ? '已绑定' : '未绑定' }}
              </span>
            </td>
            <td>{{ user.created_at }}</td>
            <td class="actions">
              <button class="action-btn" @click="showBindQR(user)" :disabled="!user.zepp_email">
                二维码
              </button>
              <button class="action-btn" @click="refreshStatus(user)" :disabled="!user.zepp_userid">
                刷新状态
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
    </div>

    <!-- 二维码弹窗 -->
    <div class="modal" v-if="showQRModal" @click.self="showQRModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>绑定二维码</h3>
          <button class="close-btn" @click="showQRModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="modal-user">用户: {{ currentUser?.user_key }}</p>
          <div class="qrcode-container" v-if="qrcodeUrl">
            <img :src="qrcodeUrl" alt="绑定二维码" />
          </div>
          <p class="loading-text" v-else>加载中...</p>
        </div>
      </div>
    </div>

    <!-- 批量注册弹窗 -->
    <div class="modal" v-if="showBatchModal" @click.self="closeBatchModal">
      <div class="modal-content batch-modal">
        <div class="modal-header">
          <h3>批量注册 Zepp 账户</h3>
          <button class="close-btn" @click="closeBatchModal">&times;</button>
        </div>
        <div class="modal-body">
          <!-- 注册表单 -->
          <div v-if="!batchResult && !batchRegistering" class="batch-form">
            <div class="form-group">
              <label>注册数量</label>
              <input
                v-model.number="batchCount"
                type="number"
                min="1"
                max="50"
                placeholder="1-50"
              />
            </div>
            <p class="form-tip">系统将自动生成随机邮箱和密码，完成注册后存入数据库</p>
            <div class="form-actions">
              <button class="cancel-btn" @click="closeBatchModal">取消</button>
              <button class="confirm-btn" @click="batchRegister">开始注册</button>
            </div>
          </div>

          <!-- 注册中 -->
          <div v-if="batchRegistering" class="batch-progress">
            <div class="spinner"></div>
            <p>{{ batchProgress || '正在注册中...' }}</p>
          </div>

          <!-- 注册结果 -->
          <div v-if="batchResult" class="batch-result">
            <div class="result-summary">
              <span class="success-count">成功: {{ batchResult.registered }}</span>
              <span class="failed-count">失败: {{ batchResult.failed }}</span>
            </div>

            <div class="accounts-list" v-if="batchResult.accounts.length">
              <h4>已注册账户</h4>
              <div class="account-item" v-for="(acc, idx) in batchResult.accounts" :key="idx">
                <div class="account-info">
                  <p><strong>邮箱:</strong> {{ acc.email }}</p>
                  <p><strong>密码:</strong> {{ acc.password }}</p>
                </div>
                <div class="account-qr" v-if="acc.qrcode">
                  <img :src="acc.qrcode" alt="二维码" />
                </div>
              </div>
            </div>

            <div class="form-actions">
              <button class="confirm-btn" @click="closeBatchModal">完成</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminUsers',
  data() {
    return {
      users: [],
      loading: false,
      keyword: '',
      bindStatus: '',
      page: 1,
      pageSize: 20,
      total: 0,
      showQRModal: false,
      currentUser: null,
      qrcodeUrl: '',
      // 批量注册
      showBatchModal: false,
      batchCount: 5,
      batchRegistering: false,
      batchProgress: '',
      batchResult: null
    }
  },
  computed: {
    totalPages() {
      return Math.ceil(this.total / this.pageSize)
    }
  },
  mounted() {
    this.loadUsers()
  },
  methods: {
    async loadUsers() {
      this.loading = true
      try {
        const params = {
          page: this.page,
          page_size: this.pageSize,
          keyword: this.keyword,
          bind_status: this.bindStatus || undefined
        }
        const res = await axios.get('/api/admin/users', { params })
        if (res.data.success) {
          this.users = res.data.data
          this.total = res.data.total
        }
      } catch (err) {
        console.error('加载用户失败:', err)
        if (err.response?.status === 401) {
          this.$router.push('/admin')
        }
      } finally {
        this.loading = false
      }
    },
    search() {
      this.page = 1
      this.loadUsers()
    },
    changePage(newPage) {
      this.page = newPage
      this.loadUsers()
    },
    async showBindQR(user) {
      this.currentUser = user
      this.showQRModal = true
      this.qrcodeUrl = ''

      try {
        const res = await axios.get(`/api/admin/users/${user.user_key}/bindqr`)
        if (res.data.success) {
          this.qrcodeUrl = res.data.qrcode
        } else {
          alert(res.data.message || '获取二维码失败')
        }
      } catch (err) {
        console.error('获取二维码失败:', err)
        alert('获取二维码失败')
      }
    },
    async refreshStatus(user) {
      try {
        const res = await axios.post(`/api/admin/users/${user.user_key}/bindstatus`)
        if (res.data.success) {
          alert(res.data.message || '刷新成功')
          this.loadUsers()
        } else {
          alert(res.data.message || '刷新失败')
        }
      } catch (err) {
        console.error('刷新状态失败:', err)
        alert('刷新状态失败')
      }
    },
    async batchRegister() {
      if (this.batchCount < 1 || this.batchCount > 50) {
        alert('注册数量范围为 1-50')
        return
      }

      this.batchRegistering = true
      this.batchProgress = '正在注册中，请稍候...'
      this.batchResult = null

      try {
        const res = await axios.post('/api/admin/batch-register', {
          count: this.batchCount
        })

        if (res.data.success) {
          this.batchResult = res.data
          this.batchProgress = ''
          this.loadUsers()
        } else {
          this.batchProgress = res.data.message || '注册失败'
        }
      } catch (err) {
        console.error('批量注册失败:', err)
        this.batchProgress = '网络错误，请重试'
      } finally {
        this.batchRegistering = false
      }
    },
    closeBatchModal() {
      this.showBatchModal = false
      this.batchResult = null
      this.batchProgress = ''
      this.batchCount = 5
    }
  }
}
</script>

<style scoped>
.admin-users {
  max-width: 1200px;
}

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.search-bar {
  display: flex;
  gap: 12px;
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

/* 表格 */
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

/* 状态标签 */
.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
}

.status-badge.bound {
  background: rgba(16, 185, 129, 0.2);
  color: #10b981;
}

.status-badge.unbound {
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
}

/* 操作按钮 */
.actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  background: transparent;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 分页 */
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

/* 弹窗 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1f2e;
  border-radius: 12px;
  width: 90%;
  max-width: 400px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-header h3 {
  color: #fff;
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.7);
  font-size: 24px;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  text-align: center;
}

.modal-user {
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 16px;
}

.qrcode-container {
  display: flex;
  justify-content: center;
}

.qrcode-container img {
  max-width: 200px;
  border-radius: 8px;
}

.loading-text {
  color: rgba(255, 255, 255, 0.5);
}

.batch-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: transform 0.2s;
}

.batch-btn:hover {
  transform: translateY(-2px);
}

.btn-icon {
  font-size: 18px;
  font-weight: bold;
}

/* 批量注册弹窗 */
.batch-modal {
  max-width: 600px;
}

.batch-form {
  text-align: left;
}

.batch-form .form-group {
  margin-bottom: 16px;
}

.batch-form label {
  display: block;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  margin-bottom: 8px;
}

.batch-form input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 14px;
}

.form-tip {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  margin-bottom: 20px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.cancel-btn {
  padding: 10px 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: transparent;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.confirm-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #4a9eff 0%, #3b82f6 100%);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.batch-progress {
  text-align: center;
  padding: 40px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #4a9eff;
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.batch-progress p {
  color: rgba(255, 255, 255, 0.7);
}

.batch-result {
  text-align: left;
}

.result-summary {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.success-count {
  color: #10b981;
}

.failed-count {
  color: #ef4444;
}

.accounts-list {
  max-height: 300px;
  overflow-y: auto;
}

.accounts-list h4 {
  color: #fff;
  font-size: 14px;
  margin-bottom: 12px;
}

.account-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 8px;
}

.account-info p {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  margin: 4px 0;
}

.account-info strong {
  color: rgba(255, 255, 255, 0.5);
}

.account-qr img {
  width: 60px;
  height: 60px;
  border-radius: 4px;
}
</style>
