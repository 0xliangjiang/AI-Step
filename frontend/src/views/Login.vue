<template>
  <div class="login-page">
    <div class="login-container">
      <!-- Logo区域 -->
      <div class="logo-section">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M13.5 5.5C14.594 5.5 15.5 4.594 15.5 3.5C15.5 2.406 14.594 1.5 13.5 1.5C12.406 1.5 11.5 2.406 11.5 3.5C11.5 4.594 12.406 5.5 13.5 5.5Z" fill="currentColor"/>
            <path d="M9.89 19.38L10.89 15L13 17V23H15V15.5L12.89 13.5L13.5 10.5C14.79 12 16.79 13 19 13V11C17.09 11 15.5 10 14.69 8.58L13.69 7C13.29 6.38 12.69 6 12 6C11.69 6 11.5 6.08 11.19 6.19L6 8.28V13H8V9.58L9.79 8.88L8.19 17L3.29 16L2.89 18L9.89 19.38Z" fill="currentColor"/>
          </svg>
        </div>
        <h1 class="logo-title">AI智能刷步系统</h1>
        <p class="logo-subtitle">自动刷步神器 - 简单高效</p>
      </div>

      <!-- 功能特点 -->
      <div class="features">
        <div class="feature-item">
          <span class="feature-icon">🎯</span>
          <div class="feature-text">
            <h4>一键刷步</h4>
            <p>AI对话即可完成刷步</p>
          </div>
        </div>
        <div class="feature-item">
          <span class="feature-icon">⏰</span>
          <div class="feature-text">
            <h4>定时任务</h4>
            <p>每天自动完成目标步数</p>
          </div>
        </div>
        <div class="feature-item">
          <span class="feature-icon">🎁</span>
          <div class="feature-text">
            <h4>新用户免费</h4>
            <p>赠送3天会员体验</p>
          </div>
        </div>
      </div>

      <!-- 登录卡片 -->
      <div class="login-card">
        <div class="card-header">
          <h2>立即开始</h2>
          <p>请输入卡密进入系统</p>
        </div>

        <div class="card-form">
          <div class="input-group">
            <label>卡密</label>
            <input
              v-model="userKey"
              type="text"
              placeholder="请输入卡密"
              @keyup.enter="login"
            />
          </div>

          <button class="login-btn" @click="login" :disabled="loading">
            <span v-if="!loading">开始使用</span>
            <span v-else class="loading-spinner"></span>
          </button>
        </div>

        <div class="card-footer">
          <p>卡密首次验证后会本地缓存，下次自动登录</p>
        </div>
      </div>

      <!-- 使用说明 -->
      <div class="usage-guide">
        <h3>使用指南</h3>
        <div class="guide-steps">
          <div class="step">
            <span class="step-num">1</span>
            <span class="step-text">输入卡密登录系统</span>
          </div>
          <div class="step">
            <span class="step-num">2</span>
            <span class="step-text">说"我要刷步"注册账号</span>
          </div>
          <div class="step">
            <span class="step-num">3</span>
            <span class="step-text">扫码绑定微信手环</span>
          </div>
          <div class="step">
            <span class="step-num">4</span>
            <span class="step-text">说"刷50000步"即可完成</span>
          </div>
        </div>
      </div>

      <!-- 底部信息 -->
      <div class="footer-info">
        <p>遇到问题？联系 QQ: 188177020</p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Login',
  data() {
    return {
      userKey: '',
      loading: false
    }
  },
  mounted() {
    const cachedUserKey = localStorage.getItem('userKey')
    if (cachedUserKey) {
      this.userKey = cachedUserKey
      this.login(true)
    }
  },
  methods: {
    async login(silent = false) {
      if (!this.userKey.trim()) {
        if (!silent) alert('请输入卡密')
        return
      }

      this.loading = true
      try {
        const res = await axios.post('/api/user/login', {
          user_key: this.userKey.trim()
        })

        if (res.data.success) {
          localStorage.setItem('userKey', this.userKey.trim())
          this.$router.push('/chat')
        }
      } catch (error) {
        localStorage.removeItem('userKey')
        const msg = error?.response?.data?.detail || '登录失败，请检查卡密后重试'
        if (!silent) alert(msg)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-container {
  width: 100%;
  max-width: 420px;
}

/* Logo区域 */
.logo-section {
  text-align: center;
  margin-bottom: 24px;
}

.logo-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
}

.logo-icon svg {
  width: 40px;
  height: 40px;
  color: white;
}

.logo-title {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.logo-subtitle {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.7);
}

/* 功能特点 */
.features {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.feature-item {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 14px 12px;
  text-align: center;
  backdrop-filter: blur(10px);
}

.feature-icon {
  font-size: 24px;
  display: block;
  margin-bottom: 8px;
}

.feature-text h4 {
  color: white;
  font-size: 13px;
  margin-bottom: 4px;
}

.feature-text p {
  color: rgba(255, 255, 255, 0.6);
  font-size: 11px;
}

/* 登录卡片 */
.login-card {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
  margin-bottom: 20px;
}

.card-header {
  text-align: center;
  margin-bottom: 24px;
}

.card-header h2 {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 6px;
}

.card-header p {
  font-size: 14px;
  color: #666;
}

.card-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-group label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.input-group input {
  padding: 14px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  font-size: 16px;
  transition: all 0.3s;
  background: #fafafa;
}

.input-group input:focus {
  outline: none;
  border-color: #667eea;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
}

.login-btn {
  padding: 14px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 50px;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.card-footer {
  margin-top: 16px;
  text-align: center;
}

.card-footer p {
  font-size: 13px;
  color: #17bf63;
  font-weight: 500;
}

/* 使用说明 */
.usage-guide {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  backdrop-filter: blur(10px);
}

.usage-guide h3 {
  color: white;
  font-size: 15px;
  margin-bottom: 16px;
  text-align: center;
}

.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step {
  display: flex;
  align-items: center;
  gap: 12px;
}

.step-num {
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-text {
  color: rgba(255, 255, 255, 0.85);
  font-size: 13px;
}

/* 底部信息 */
.footer-info {
  text-align: center;
}

.footer-info p {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}
</style>
