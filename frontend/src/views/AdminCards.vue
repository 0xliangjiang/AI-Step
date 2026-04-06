<template>
  <div class="admin-page">
    <div class="page-header">
      <h2>卡密管理</h2>
      <p>生成和管理充值卡密</p>
    </div>

    <!-- 统计栏 -->
    <div class="stats-row" v-if="stats">
      <div class="stat-card">
        <div class="stat-num">{{ stats.total }}</div>
        <div class="stat-label">总卡密</div>
      </div>
      <div class="stat-card unused">
        <div class="stat-num">{{ stats.unused }}</div>
        <div class="stat-label">未使用</div>
      </div>
      <div class="stat-card used">
        <div class="stat-num">{{ stats.used }}</div>
        <div class="stat-label">已使用</div>
      </div>
      <div class="stat-breakdown" v-if="stats.days_breakdown.length">
        <span v-for="item in stats.days_breakdown" :key="item.days" class="breakdown-item">
          {{ item.days }}天 × {{ item.count }}张
        </span>
      </div>
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
        <div class="result-actions">
          <button class="btn-action" @click="copyGeneratedCards">
            {{ copyBtnText }}
          </button>
          <button class="btn-action export" @click="downloadGeneratedCards">
            下载 TXT
          </button>
        </div>
      </div>
      <div class="card-list">
        <div
          class="card-item"
          v-for="card in generatedCards"
          :key="card.card_key"
          @click="copySingleCard(card.card_key)"
          title="点击复制"
        >
          <span class="card-key">{{ card.card_key }}</span>
          <span class="card-days">{{ card.days }}天</span>
          <span class="copy-hint">点击复制</span>
        </div>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <select v-model="filterStatus" @change="onFilterChange">
        <option value="">全部状态</option>
        <option value="unused">未使用</option>
        <option value="used">已使用</option>
      </select>
      <select v-model="filterDays" @change="onFilterChange">
        <option value="0">全部天数</option>
        <option v-for="item in stats && stats.days_breakdown" :key="item.days" :value="item.days">
          {{ item.days }} 天
        </option>
      </select>
      <button class="btn-refresh" @click="loadCards">刷新</button>
      <button class="btn-export" @click="exportCSV">导出 CSV</button>
      <button class="btn-export txt" @click="exportTXT">导出 TXT</button>
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
            <td>
              <code @click="copySingleCard(card.card_key)" class="copyable" title="点击复制">
                {{ card.card_key }}
              </code>
            </td>
            <td>{{ card.days }} 天</td>
            <td>
              <span :class="['status-badge', card.status]">
                {{ card.status === 'unused' ? '未使用' : '已使用' }}
              </span>
            </td>
            <td class="text-muted">{{ card.used_by || '-' }}</td>
            <td class="text-muted">{{ card.used_at || '-' }}</td>
            <td class="text-muted">{{ card.created_at }}</td>
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

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页，共 {{ total }} 条</span>
      <button :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
    </div>

    <!-- 复制提示 toast -->
    <div class="toast" v-if="toastMsg" :class="{ show: toastMsg }">{{ toastMsg }}</div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminCards',
  data() {
    return {
      generateForm: { count: 10, days: 30 },
      generating: false,
      generatedCards: [],
      cards: [],
      total: 0,
      page: 1,
      pageSize: 20,
      filterStatus: '',
      filterDays: 0,
      stats: null,
      copyBtnText: '复制全部',
      toastMsg: '',
      toastTimer: null
    }
  },
  computed: {
    totalPages() {
      return Math.ceil(this.total / this.pageSize)
    }
  },
  mounted() {
    this.loadStats()
    this.loadCards()
  },
  methods: {
    token() {
      return localStorage.getItem('adminToken')
    },

    showToast(msg) {
      this.toastMsg = msg
      if (this.toastTimer) clearTimeout(this.toastTimer)
      this.toastTimer = setTimeout(() => { this.toastMsg = '' }, 2000)
    },

    // 兼容 HTTP 环境的复制方法
    async copyText(text) {
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(text)
        } else {
          // fallback for HTTP
          const ta = document.createElement('textarea')
          ta.value = text
          ta.style.position = 'fixed'
          ta.style.opacity = '0'
          document.body.appendChild(ta)
          ta.focus()
          ta.select()
          document.execCommand('copy')
          document.body.removeChild(ta)
        }
        return true
      } catch {
        return false
      }
    },

    async copySingleCard(key) {
      const ok = await this.copyText(key)
      this.showToast(ok ? `已复制：${key}` : '复制失败，请手动选择')
    },

    async copyGeneratedCards() {
      const text = this.generatedCards.map(c => `${c.card_key}`).join('\n')
      const ok = await this.copyText(text)
      if (ok) {
        this.copyBtnText = '已复制 ✓'
        setTimeout(() => { this.copyBtnText = '复制全部' }, 2000)
      } else {
        this.showToast('复制失败，请手动复制')
      }
    },

    downloadGeneratedCards() {
      const text = this.generatedCards.map(c => `${c.card_key}  (${c.days}天)`).join('\n')
      this.downloadFile(text, `cards_${this.generatedCards[0].days}days.txt`, 'text/plain')
    },

    downloadFile(content, filename, type) {
      const blob = new Blob([content], { type })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    },

    async exportCSV() {
      try {
        const params = new URLSearchParams()
        if (this.filterStatus) params.set('status', this.filterStatus)
        if (this.filterDays) params.set('days', this.filterDays)
        const url = `/api/admin/cards/export?${params}&_t=${Date.now()}`
        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${this.token()}` }
        })
        const blob = await res.blob()
        this.downloadFile(await blob.text(), 'cards.csv', 'text/csv;charset=utf-8-sig')
        this.showToast('CSV 已下载')
      } catch {
        this.showToast('导出失败')
      }
    },

    async exportTXT() {
      try {
        const params = new URLSearchParams()
        if (this.filterStatus) params.set('status', this.filterStatus)
        if (this.filterDays) params.set('days', this.filterDays)
        // 拉取全量数据
        const res = await axios.get('/api/admin/cards', {
          params: { status: this.filterStatus, days: this.filterDays || 0, page: 1, page_size: 9999 },
          headers: { Authorization: `Bearer ${this.token()}` }
        })
        const cards = res.data.data || []
        const lines = cards.map(c =>
          c.status === 'unused'
            ? c.card_key
            : `${c.card_key}  [已使用]`
        )
        this.downloadFile(lines.join('\n'), 'cards.txt', 'text/plain;charset=utf-8')
        this.showToast(`已导出 ${cards.length} 条`)
      } catch {
        this.showToast('导出失败')
      }
    },

    async loadStats() {
      try {
        const res = await axios.get('/api/admin/cards/stats', {
          headers: { Authorization: `Bearer ${this.token()}` }
        })
        if (res.data.success) this.stats = res.data.data
      } catch { /* ignore */ }
    },

    async loadCards() {
      try {
        const res = await axios.get('/api/admin/cards', {
          params: {
            page: this.page,
            page_size: this.pageSize,
            status: this.filterStatus,
            days: this.filterDays || 0
          },
          headers: { Authorization: `Bearer ${this.token()}` }
        })
        this.cards = res.data.data || []
        this.total = res.data.total || 0
      } catch (error) {
        console.error('加载卡密失败:', error)
      }
    },

    onFilterChange() {
      this.page = 1
      this.loadCards()
    },

    changePage(p) {
      this.page = p
      this.loadCards()
    },

    async generateCards() {
      if (this.generateForm.count < 1 || this.generateForm.count > 100) {
        alert('生成数量范围 1-100')
        return
      }
      this.generating = true
      try {
        const res = await axios.post('/api/admin/cards/generate', this.generateForm, {
          headers: { Authorization: `Bearer ${this.token()}` }
        })
        if (res.data.success) {
          this.generatedCards = res.data.cards
          this.showToast(res.data.message)
          this.loadCards()
          this.loadStats()
        } else {
          alert(res.data.message)
        }
      } catch {
        alert('生成失败')
      } finally {
        this.generating = false
      }
    },

    async deleteCard(card) {
      if (!confirm('确定删除该卡密？')) return
      try {
        await axios.delete(`/api/admin/cards/${card.id}`, {
          headers: { Authorization: `Bearer ${this.token()}` }
        })
        this.showToast('已删除')
        this.loadCards()
        this.loadStats()
      } catch (error) {
        alert(error.response?.data?.message || '删除失败')
      }
    }
  }
}
</script>

<style scoped>
.admin-page {
  padding: 20px;
  position: relative;
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

/* 统计栏 */
.stats-row {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.stat-card {
  background: #192734;
  border-radius: 10px;
  padding: 14px 20px;
  text-align: center;
  min-width: 80px;
}

.stat-card.unused .stat-num { color: #1da1f2; }
.stat-card.used .stat-num { color: #8899a6; }

.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
}

.stat-label {
  font-size: 12px;
  color: #8899a6;
  margin-top: 4px;
}

.stat-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.breakdown-item {
  background: #22303c;
  color: #8899a6;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
}

/* 生成区 */
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

.btn-generate:hover:not(:disabled) { background: #1a91da; }
.btn-generate:disabled { opacity: 0.6; cursor: not-allowed; }

/* 生成结果 */
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

.result-header h4 { color: #17bf63; font-size: 14px; }

.result-actions { display: flex; gap: 8px; }

.btn-action {
  padding: 6px 14px;
  border: 1px solid #38444d;
  border-radius: 6px;
  background: transparent;
  color: #8899a6;
  font-size: 12px;
  cursor: pointer;
}

.btn-action:hover { background: #22303c; color: #fff; }
.btn-action.export { border-color: #17bf63; color: #17bf63; }
.btn-action.export:hover { background: rgba(23, 191, 99, 0.1); }

.card-list {
  max-height: 220px;
  overflow-y: auto;
}

.card-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #22303c;
  border-radius: 6px;
  margin-bottom: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.card-item:hover { background: #2d3f52; }
.card-item:hover .copy-hint { opacity: 1; }

.card-key { font-family: monospace; color: #fff; flex: 1; }
.card-days { color: #8899a6; font-size: 13px; }
.copy-hint { font-size: 11px; color: #1da1f2; opacity: 0; transition: opacity 0.15s; }

/* 筛选栏 */
.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.filter-bar select {
  padding: 9px 14px;
  border: 1px solid #38444d;
  border-radius: 8px;
  background: #192734;
  color: #fff;
  font-size: 14px;
}

.btn-refresh {
  padding: 9px 18px;
  border: none;
  border-radius: 8px;
  background: #192734;
  color: #8899a6;
  font-size: 14px;
  cursor: pointer;
  border: 1px solid #38444d;
}

.btn-refresh:hover { color: #fff; }

.btn-export {
  padding: 9px 18px;
  border: none;
  border-radius: 8px;
  background: #17bf63;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-export:hover { background: #15a857; }
.btn-export.txt { background: #5c6bc0; }
.btn-export.txt:hover { background: #4a59b0; }

/* 表格 */
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
  padding: 14px 16px;
  text-align: left;
  font-weight: 600;
  color: #8899a6;
  font-size: 13px;
  border-bottom: 1px solid #38444d;
}

.data-table td {
  padding: 14px 16px;
  color: #fff;
  border-bottom: 1px solid #38444d;
  font-size: 14px;
}

.data-table tr:last-child td { border-bottom: none; }

code.copyable {
  font-family: monospace;
  background: #22303c;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

code.copyable:hover { background: #2d3f52; color: #1da1f2; }

.text-muted { color: #8899a6 !important; }

.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.unused { background: rgba(29, 161, 242, 0.15); color: #1da1f2; }
.status-badge.used { background: rgba(136, 153, 166, 0.15); color: #8899a6; }

.btn-small {
  padding: 5px 10px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.btn-danger { background: #e0245e; color: #fff; }
.btn-danger:hover { background: #c01e52; }

.empty-text {
  text-align: center;
  color: #8899a6;
  padding: 40px !important;
}

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
  color: #8899a6;
  font-size: 14px;
}

.pagination button {
  padding: 7px 16px;
  border: 1px solid #38444d;
  border-radius: 8px;
  background: #192734;
  color: #fff;
  cursor: pointer;
  font-size: 13px;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination button:not(:disabled):hover {
  background: #22303c;
}

/* Toast */
.toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  pointer-events: none;
  z-index: 9999;
  backdrop-filter: blur(4px);
}
</style>
