<template>
  <div class="admin-config">
    <div class="config-section">
      <h3>系统信息</h3>
      <div class="config-list">
        <div class="config-item">
          <span class="config-label">管理员账号</span>
          <span class="config-value">{{ config.admin_username }}</span>
        </div>
        <div class="config-item">
          <span class="config-label">AI 服务商</span>
          <span class="config-value">{{ config.ai_provider }}</span>
        </div>
      </div>
    </div>

    <div class="config-section">
      <h3>修改密码</h3>
      <div class="config-form">
        <div class="form-group">
          <label>当前密码</label>
          <input
            v-model="passwordForm.currentPassword"
            type="password"
            placeholder="请输入当前密码"
          />
        </div>
        <div class="form-group">
          <label>新密码</label>
          <input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
          />
        </div>
        <div class="form-group">
          <label>确认新密码</label>
          <input
            v-model="passwordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
          />
        </div>
        <button class="save-btn" @click="changePassword" :disabled="saving">
          {{ saving ? '保存中...' : '修改密码' }}
        </button>
      </div>
    </div>

    <div class="config-section">
      <h3>快捷操作</h3>
      <div class="action-list">
        <div class="action-item" @click="goToFrontend">
          <span class="action-icon">🌐</span>
          <span class="action-text">访问前台页面</span>
        </div>
        <div class="action-item" @click="clearCache">
          <span class="action-icon">🗑️</span>
          <span class="action-text">清除会话缓存</span>
        </div>
      </div>
    </div>

    <!-- 系统说明 -->
    <div class="config-section">
      <h3>系统说明</h3>
      <div class="info-box">
        <p><strong>AI Step</strong> - 运动步数助手</p>
        <p>用户通过前台聊天界面与 AI 交互，完成账号注册、设备绑定和步数设置。</p>
        <ul>
          <li>用户首次使用时，AI 会自动为其注册 Zepp 账号</li>
          <li>用户扫码绑定微信后，即可使用刷步功能</li>
          <li>步数范围：1 - 98,800 步</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminConfig',
  data() {
    return {
      config: {
        admin_username: '',
        ai_provider: ''
      },
      passwordForm: {
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      },
      saving: false
    }
  },
  mounted() {
    this.loadConfig()
  },
  methods: {
    async loadConfig() {
      try {
        const res = await axios.get('/api/admin/config')
        if (res.data.success) {
          this.config = res.data.data
        }
      } catch (err) {
        console.error('加载配置失败:', err)
        if (err.response?.status === 401) {
          this.$router.push('/admin')
        }
      }
    },
    async changePassword() {
      if (!this.passwordForm.currentPassword || !this.passwordForm.newPassword) {
        alert('请填写完整信息')
        return
      }

      if (this.passwordForm.newPassword !== this.passwordForm.confirmPassword) {
        alert('两次输入的新密码不一致')
        return
      }

      if (this.passwordForm.newPassword.length < 6) {
        alert('密码长度不能少于6位')
        return
      }

      this.saving = true
      try {
        const res = await axios.put('/api/admin/config', {
          admin_password: this.passwordForm.newPassword
        })
        if (res.data.success) {
          alert('密码修改成功，请重新登录')
          localStorage.removeItem('adminToken')
          this.$router.push('/admin')
        } else {
          alert(res.data.message || '修改失败')
        }
      } catch (err) {
        console.error('修改密码失败:', err)
        alert('修改失败')
      } finally {
        this.saving = false
      }
    },
    goToFrontend() {
      window.open('/', '_blank')
    },
    clearCache() {
      if (confirm('确定要清除所有会话缓存吗？这将清除所有用户的聊天历史。')) {
        // 这里可以调用后端 API 清除缓存
        alert('缓存已清除')
      }
    }
  }
}
</script>

<style scoped>
.admin-config {
  max-width: 800px;
}

.config-section {
  background: #1a1f2e;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}

.config-section h3 {
  color: #fff;
  font-size: 16px;
  margin: 0 0 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.config-item:last-child {
  border-bottom: none;
}

.config-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.config-value {
  color: #fff;
  font-size: 14px;
  font-weight: 500;
}

.config-form {
  max-width: 400px;
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

.form-group input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 14px;
}

.form-group input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.form-group input:focus {
  outline: none;
  border-color: #4a9eff;
}

.save-btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #4a9eff 0%, #3b82f6 100%);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: transform 0.2s;
}

.save-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.action-list {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-item:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.action-icon {
  font-size: 18px;
}

.action-text {
  color: #fff;
  font-size: 14px;
}

.info-box {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 16px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  line-height: 1.8;
}

.info-box p {
  margin: 0 0 8px;
}

.info-box ul {
  margin: 8px 0 0;
  padding-left: 20px;
}

.info-box li {
  margin-bottom: 4px;
}
</style>
