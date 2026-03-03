<template>
  <div class="admin-packages">
    <div class="page-header">
      <h2>VIP套餐管理</h2>
      <button class="add-btn" @click="showAddModal = true">+ 添加套餐</button>
    </div>

    <!-- 套餐列表 -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>排序</th>
            <th>套餐名称</th>
            <th>天数</th>
            <th>价格</th>
            <th>原价</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pkg in packages" :key="pkg.id">
            <td>{{ pkg.sort_order }}</td>
            <td>{{ pkg.name }}</td>
            <td>{{ pkg.days }}天</td>
            <td>¥{{ (pkg.price / 100).toFixed(2) }}</td>
            <td>{{ pkg.original_price ? '¥' + (pkg.original_price / 100).toFixed(2) : '-' }}</td>
            <td>
              <span :class="['status-badge', pkg.status === 1 ? 'active' : 'inactive']">
                {{ pkg.status === 1 ? '启用' : '禁用' }}
              </span>
            </td>
            <td>
              <button class="action-btn edit" @click="editPackage(pkg)">编辑</button>
              <button class="action-btn delete" @click="deletePackage(pkg.id)">删除</button>
            </td>
          </tr>
          <tr v-if="packages.length === 0">
            <td colspan="7" class="empty-row">暂无套餐数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 添加/编辑弹窗 -->
    <div class="modal" v-if="showAddModal" @click.self="closeModal">
      <div class="modal-content">
        <h3>{{ editingPackage ? '编辑套餐' : '添加套餐' }}</h3>
        <div class="form-group">
          <label>套餐名称</label>
          <input v-model="form.name" type="text" placeholder="如：月卡、季卡、年卡" />
        </div>
        <div class="form-group">
          <label>会员天数</label>
          <input v-model.number="form.days" type="number" min="1" placeholder="如：30" />
        </div>
        <div class="form-group">
          <label>价格（元）</label>
          <input v-model.number="form.priceYuan" type="number" step="0.01" min="0.01" placeholder="如：9.9" />
        </div>
        <div class="form-group">
          <label>原价（元）</label>
          <input v-model.number="form.originalPriceYuan" type="number" step="0.01" min="0" placeholder="可选" />
        </div>
        <div class="form-group">
          <label>排序</label>
          <input v-model.number="form.sort_order" type="number" min="0" placeholder="数字越小越靠前" />
        </div>
        <div class="form-group">
          <label>状态</label>
          <select v-model.number="form.status">
            <option :value="1">启用</option>
            <option :value="0">禁用</option>
          </select>
        </div>
        <div class="modal-actions">
          <button class="cancel-btn" @click="closeModal">取消</button>
          <button class="confirm-btn" @click="savePackage" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminPackages',
  data() {
    return {
      packages: [],
      showAddModal: false,
      editingPackage: null,
      saving: false,
      form: {
        name: '',
        days: 30,
        priceYuan: 0,
        originalPriceYuan: null,
        sort_order: 0,
        status: 1
      }
    }
  },
  mounted() {
    this.loadPackages()
  },
  methods: {
    async loadPackages() {
      try {
        const res = await axios.get('/api/admin/packages')
        if (res.data.success) {
          this.packages = res.data.data
        }
      } catch (err) {
        console.error('加载套餐失败:', err)
      }
    },
    editPackage(pkg) {
      this.editingPackage = pkg
      this.form = {
        name: pkg.name,
        days: pkg.days,
        priceYuan: pkg.price / 100,
        originalPriceYuan: pkg.original_price ? pkg.original_price / 100 : null,
        sort_order: pkg.sort_order,
        status: pkg.status
      }
      this.showAddModal = true
    },
    async savePackage() {
      if (!this.form.name || !this.form.days || !this.form.priceYuan) {
        alert('请填写完整信息')
        return
      }

      this.saving = true
      try {
        const data = {
          name: this.form.name,
          days: this.form.days,
          price: Math.round(this.form.priceYuan * 100),
          original_price: this.form.originalPriceYuan ? Math.round(this.form.originalPriceYuan * 100) : null,
          sort_order: this.form.sort_order,
          status: this.form.status
        }

        let res
        if (this.editingPackage) {
          res = await axios.put(`/api/admin/packages/${this.editingPackage.id}`, data)
        } else {
          res = await axios.post('/api/admin/packages', data)
        }

        if (res.data.success) {
          this.closeModal()
          this.loadPackages()
        } else {
          alert(res.data.message || '保存失败')
        }
      } catch (err) {
        console.error('保存套餐失败:', err)
        alert('保存失败')
      } finally {
        this.saving = false
      }
    },
    async deletePackage(id) {
      if (!confirm('确定要删除这个套餐吗？')) return

      try {
        const res = await axios.delete(`/api/admin/packages/${id}`)
        if (res.data.success) {
          this.loadPackages()
        } else {
          alert(res.data.message || '删除失败')
        }
      } catch (err) {
        console.error('删除套餐失败:', err)
        alert('删除失败')
      }
    },
    closeModal() {
      this.showAddModal = false
      this.editingPackage = null
      this.form = {
        name: '',
        days: 30,
        priceYuan: 0,
        originalPriceYuan: null,
        sort_order: 0,
        status: 1
      }
    }
  }
}
</script>

<style scoped>
.admin-packages {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  color: #fff;
  font-size: 20px;
  margin: 0;
}

.add-btn {
  padding: 10px 20px;
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
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.data-table th {
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: #fff;
  font-size: 14px;
}

.empty-row {
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  padding: 40px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
}

.status-badge.active {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.status-badge.inactive {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  margin-right: 8px;
}

.action-btn.edit {
  background: rgba(74, 158, 255, 0.2);
  color: #4a9eff;
}

.action-btn.delete {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

/* 弹窗样式 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1f2e;
  border-radius: 12px;
  padding: 24px;
  width: 400px;
  max-width: 90%;
}

.modal-content h3 {
  color: #fff;
  font-size: 18px;
  margin: 0 0 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  margin-bottom: 8px;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 14px;
}

.form-group select {
  cursor: pointer;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.cancel-btn,
.confirm-btn {
  flex: 1;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.confirm-btn {
  background: linear-gradient(135deg, #4a9eff 0%, #3b82f6 100%);
  color: #fff;
}

.confirm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
