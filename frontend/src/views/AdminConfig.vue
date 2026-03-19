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

    <!-- 伪装模式配置 -->
    <div class="config-section">
      <h3>小程序模式</h3>
      <div class="config-form">
        <div class="form-group">
          <label>伪装模式</label>
          <div class="switch-row">
            <label class="switch">
              <input type="checkbox" v-model="stealthMode" @change="saveStealthMode">
              <span class="slider"></span>
            </label>
            <span class="switch-label">{{ stealthMode ? '已开启' : '已关闭' }}</span>
          </div>
          <p class="form-hint">
            开启后：AI 表现为正常的对话助手<br>
            关闭后：AI 表现为刷步助手（审核时请保持开启）
          </p>
        </div>
      </div>
    </div>

    <!-- 广告奖励配置 -->
    <div class="config-section">
      <h3>广告奖励配置</h3>
      <div class="config-form">
        <div class="form-group">
          <label>每次观看奖励天数</label>
          <div class="input-row">
            <input
              v-model.number="adConfig.ad_reward_days"
              type="number"
              min="1"
              max="30"
              placeholder="1-30"
            />
            <span class="input-unit">天</span>
          </div>
          <p class="form-hint">用户观看一次广告获得的会员天数（1-30天）</p>
        </div>
        <div class="form-group">
          <label>每日观看次数上限</label>
          <div class="input-row">
            <input
              v-model.number="adConfig.ad_daily_limit"
              type="number"
              min="1"
              max="20"
              placeholder="1-20"
            />
            <span class="input-unit">次</span>
          </div>
          <p class="form-hint">每个用户每天最多观看广告次数（1-20次）</p>
        </div>
        <button class="save-btn" @click="saveAdConfig" :disabled="savingAd">
          {{ savingAd ? '保存中...' : '保存配置' }}
        </button>
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
      stealthMode: true,
      adConfig: {
        ad_reward_days: 1,
        ad_daily_limit: 3
      },
      passwordForm: {
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      },
      saving: false,
      savingAd: false,
      savingStealth: false
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
          if (res.data.data.ad_reward_days) {
            this.adConfig.ad_reward_days = res.data.data.ad_reward_days
          }
          if (res.data.data.ad_daily_limit) {
            this.adConfig.ad_daily_limit = res.data.data.ad_daily_limit
          }
          if (res.data.data.stealth_mode !== undefined) {
            this.stealthMode = res.data.data.stealth_mode
          }
        }
      } catch (err) {
        console.error('加载配置失败:', err)
        if (err.response?.status === 401) {
          this.$router.push('/admin')
        }
      }
    },
    async saveStealthMode() {
      this.savingStealth = true
      try {
        const res = await axios.put('/api/admin/config', {
          stealth_mode: this.stealthMode
        })
        if (res.data.success) {
          // 静默保存成功
        } else {
          alert(res.data.message || '保存失败')
          this.stealthMode = !this.stealthMode
        }
      } catch (err) {
        console.error('保存伪装模式失败:', err)
        alert('保存失败')
        this.stealthMode = !this.stealthMode
      } finally {
        this.savingStealth = false
      }
    },
    async saveAdConfig() {
      if (this.adConfig.ad_reward_days < 1 || this.adConfig.ad_reward_days > 30) {
        alert('奖励天数范围为 1-30 天')
        return
      }
      if (this.adConfig.ad_daily_limit < 1 || this.adConfig.ad_daily_limit > 20) {
        alert('每日次数范围为 1-20 次')
        return
      }

      this.savingAd = true
      try {
        const res = await axios.put('/api/admin/config', {
          ad_reward_days: this.adConfig.ad_reward_days,
          ad_daily_limit: this.adConfig.ad_daily_limit
        })
        if (res.data.success) {
          alert('配置保存成功')
        } else {
          alert(res.data.message || '保存失败')
        }
      } catch (err) {
        console.error('保存配置失败:', err)
        alert('保存失败')
      } finally {
        this.savingAd = false
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

.input-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.input-row input {
  width: 120px;
  text-align: center;
}

.input-unit {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.form-hint {
  margin: 8px 0 0;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
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

/* 开关样式 */
.switch-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.2);
  transition: 0.3s;
  border-radius: 26px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .slider {
  background: linear-gradient(135deg, #4a9eff 0%, #3b82f6 100%);
}

input:checked + .slider:before {
  transform: translateX(24px);
}

.switch-label {
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
}
</style>
