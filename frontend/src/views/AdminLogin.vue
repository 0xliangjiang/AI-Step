<template>
  <div class="admin-login-page">
    <div class="admin-container">
      <div class="admin-card">
        <div class="admin-header">
          <h1>管理后台</h1>
          <p>AI智能刷步系统</p>
        </div>
        <div class="admin-form">
          <input
            v-model="username"
            type="text"
            placeholder="管理员账号"
            @keyup.enter="login"
          />
          <input
            v-model="password"
            type="password"
            placeholder="密码"
            @keyup.enter="login"
          />
          <button class="admin-btn" @click="login" :disabled="loading">
            {{ loading ? '登录中...' : '登录' }}
          </button>
          <p v-if="error" class="error-msg">{{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AdminLogin',
  data() {
    return {
      username: '',
      password: '',
      loading: false,
      error: ''
    }
  },
  methods: {
    async login() {
      if (!this.username || !this.password) {
        this.error = '请输入账号和密码'
        return
      }

      this.loading = true
      this.error = ''

      try {
        const res = await axios.post('/api/admin/login', {
          username: this.username,
          password: this.password
        })

        if (res.data.success) {
          localStorage.setItem('adminToken', res.data.token)
          this.$router.push('/admin/dashboard/users')
        } else {
          this.error = res.data.message || '登录失败'
        }
      } catch (err) {
        this.error = '网络错误，请重试'
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.admin-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.admin-container {
  width: 100%;
  max-width: 400px;
  padding: 20px;
}

.admin-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  overflow: hidden;
}

.admin-header {
  padding: 40px 30px 20px;
  text-align: center;
}

.admin-header h1 {
  font-size: 24px;
  color: #fff;
  margin-bottom: 8px;
}

.admin-header p {
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
}

.admin-form {
  padding: 20px 30px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.admin-form input {
  width: 100%;
  padding: 14px 16px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 15px;
  transition: border-color 0.3s;
}

.admin-form input::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.admin-form input:focus {
  outline: none;
  border-color: #4a9eff;
}

.admin-btn {
  padding: 14px 24px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #4a9eff 0%, #3b82f6 100%);
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.admin-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(74, 158, 255, 0.4);
}

.admin-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-msg {
  color: #ff6b6b;
  font-size: 14px;
  text-align: center;
  margin: 0;
}
</style>
