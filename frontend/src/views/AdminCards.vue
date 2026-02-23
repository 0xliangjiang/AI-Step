<template>
  <div class="admin-page">
    <div class="page-header">
      <h2>卡密管理</h2>
      <p>生成和管理充值卡密</p>
    </div>

    <!-- 生成卡密 -->
    <div class="generate-card">
      <h3>批量生成卡密</h3>
      <div class="form-row">
        <div class="form-group">
          <label>生成数量</label>
          <input type="number" v-model="generateForm.count" min="1" max="100" />
        </div>
        <div class="form-group">
          <label>天数</label>
          <input type="number" v-model="generateForm.days" min="1" max="365" />
        </div>
        <button class="btn-generate" @click="generateCards" :disabled="generating">
          {{ generating ? '生成中...' : '生成卡密' }}
        </button>
      </div>
    </div>

    <!-- 生成结果 -->
    <div class="generate-result" v-if="generatedCards.length > 0">
      <div class="result-header">
        <h4>生成成功 ({{ generatedCards.length }} 张)</h4>
        <button class="btn-copy" @click="copyCards">复制全部</button>
      </div>
      <div class="card-list">
        <div class="card-item" v-for="card in generatedCards" :key="card.card_key">
          <span class="card-key">{{ card.card_key }}</span>
          <span class="card-days">{{ card.days }}天</span>
        </div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <select v-model="filterStatus" @change="loadCards">
        <option value="">全部状态</option>
        <option value="unused">未使用</option>
        <option value="used">已使用</option>
      </select>
      <button class="btn-refresh" @click="loadCards">刷新</button>
    </div>

    <!-- 卡密列表 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>卡密</th>
            <th>天数</th>
            <th>状态</th>
            <th>使用者</th>
            <th>使用时间</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="card in cards" :key="card.id">
            <td><code>{{ card.card_key }}</code></td>
            <td>{{ card.days }} 天</td>
            <td>
              <span :class="['status-badge', card.status]">
                {{ card.status === 'unused' ? '未使用' : '已使用' }}
              </span>
            </td>
            <td>{{ card.used_by || '-' }}</td>
            <td>{{ card.used_at || '-' }}</td>
            <td>{{ card.created_at }}</td>
            <td>
              <button
                v-if="card.status === 'unused'"
                class="btn-small btn-danger"
                @click="deleteCard(card)"
              >
                删除
              </button>
            </td>
          </tr>
          <tr v-if="cards.length === 0">
            <td colspan="7" class="empty-text">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 统计 -->
    <div class="stats-bar" v-if="cards.length > 0">
      <span>共 {{ total }} 张卡密</span>
      <span>未使用: {{ cards.filter(c => c.status === 'unused').length }}</span>
      <span>已使用: {{ cards.filter(c => c.status === 'used').length }}</span>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminCards',
  data() {
    return {
      generateForm: {
        count: 10,
        days: 30
      },
      generating: false,
      generatedCards: [],
      cards: [],
      total: 0,
      filterStatus: ''
    }
  },
  mounted() {
    this.loadCards()
  },
  methods: {
    async generateCards() {
      if (this.generateForm.count < 1 || this.generateForm.count > 100) {
        alert('生成数量范围 1-100')
        return
      }

      this.generating = true
      try {
        const token = localStorage.getItem('adminToken')
        const res = await axios.post('/api/admin/cards/generate', this.generateForm, {
          headers: { Authorization: `Bearer ${token}` }
        })

        if (res.data.success) {
          this.generatedCards = res.data.cards
          alert(res.data.message)
          this.loadCards()
        } else {
          alert(res.data.message)
        }
      } catch (error) {
        alert('生成失败')
      } finally {
        this.generating = false
      }
    },

    async loadCards() {
      try {
        const token = localStorage.getItem('adminToken')
        const res = await axios.get('/api/admin/cards', {
          params: { status: this.filterStatus },
          headers: { Authorization: `Bearer ${token}` }
        })
        this.cards = res.data.data || []
        this.total = res.data.total || 0
      } catch (error) {
        console.error('加载卡密失败:', error)
      }
    },

    async deleteCard(card) {
      if (!confirm('确定删除该卡密？')) return
      try {
        const token = localStorage.getItem('adminToken')
        await axios.delete(`/api/admin/cards/${card.id}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        this.loadCards()
      } catch (error) {
        alert(error.response?.data?.message || '删除失败')
      }
    },

    copyCards() {
      const text = this.generatedCards.map(c => `${c.card_key} (${c.days}天)`).join('\n')
      navigator.clipboard.writeText(text).then(() => {
        alert('已复制到剪贴板')
      })
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

.generate-card {
  background: #192734;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.generate-card h3 {
  color: #fff;
  font-size: 16px;
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  color: #8899a6;
  font-size: 13px;
}

.form-group input {
  width: 120px;
  padding: 10px 14px;
  border: 1px solid #38444d;
  border-radius: 8px;
  background: #22303c;
  color: #fff;
  font-size: 14px;
}

.btn-generate {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  background: #1da1f2;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-generate:hover:not(:disabled) {
  background: #1a91da;
}

.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.generate-result {
  background: #192734;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.result-header h4 {
  color: #17bf63;
  font-size: 14px;
}

.btn-copy {
  padding: 6px 12px;
  border: 1px solid #38444d;
  border-radius: 6px;
  background: transparent;
  color: #8899a6;
  font-size: 12px;
  cursor: pointer;
}

.btn-copy:hover {
  background: #22303c;
  color: #fff;
}

.card-list {
  max-height: 200px;
  overflow-y: auto;
}

.card-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  background: #22303c;
  border-radius: 6px;
  margin-bottom: 8px;
}

.card-key {
  font-family: monospace;
  color: #fff;
}

.card-days {
  color: #8899a6;
  font-size: 13px;
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
  border-bottom: 1px solid #38444d;
}

.data-table td {
  padding: 16px;
  color: #fff;
  border-bottom: 1px solid #38444d;
}

.data-table code {
  font-family: monospace;
  background: #22303c;
  padding: 4px 8px;
  border-radius: 4px;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.unused {
  background: rgba(29, 161, 242, 0.2);
  color: #1da1f2;
}

.status-badge.used {
  background: rgba(136, 153, 166, 0.2);
  color: #8899a6;
}

.btn-small {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
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
