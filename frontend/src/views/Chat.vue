<template>
  <div class="chat-page">
    <div class="chat-container">
      <!-- Header -->
      <header class="chat-header">
        <div class="header-left">
          <div class="header-icon">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M13.5 5.5C14.594 5.5 15.5 4.594 15.5 3.5C15.5 2.406 14.594 1.5 13.5 1.5C12.406 1.5 11.5 2.406 11.5 3.5C11.5 4.594 12.406 5.5 13.5 5.5Z" fill="currentColor"/>
              <path d="M9.89 19.38L10.89 15L13 17V23H15V15.5L12.89 13.5L13.5 10.5C14.79 12 16.79 13 19 13V11C17.09 11 15.5 10 14.69 8.58L13.69 7C13.29 6.38 12.69 6 12 6C11.69 6 11.5 6.08 11.19 6.19L6 8.28V13H8V9.58L9.79 8.88L8.19 17L3.29 16L2.89 18L9.89 19.38Z" fill="currentColor"/>
            </svg>
          </div>
          <div class="header-title">
            <h1>AI智能刷步</h1>
            <span class="status-dot"></span>
            <span class="status-text">在线</span>
          </div>
        </div>
        <div class="header-right">
          <!-- VIP状态 -->
          <div class="vip-badge" :class="{ active: userInfo.is_vip, expired: !userInfo.is_vip }" @click="showVipInfo = true">
            <span v-if="userInfo.is_vip">VIP {{ userInfo.remaining_days }}天</span>
            <span v-else>已过期</span>
          </div>
          <button class="logout-btn" @click="logout" title="退出登录">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M17 7L15.59 8.41L18.17 11H8V13H18.17L15.59 15.58L17 17L22 12L17 7ZM4 5H12V3H4C2.9 3 2 3.9 2 5V19C2 20.1 2.9 21 4 21H12V19H4V5Z" fill="currentColor"/>
            </svg>
          </button>
        </div>
      </header>

      <!-- VIP信息弹窗 -->
      <div class="vip-modal" v-if="showVipInfo" @click.self="showVipInfo = false">
        <div class="vip-modal-content">
          <h3>会员信息</h3>
          <div class="vip-info-item">
            <span class="label">会员状态</span>
            <span class="value" :class="{ active: userInfo.is_vip }">
              {{ userInfo.is_vip ? '有效' : '已过期' }}
            </span>
          </div>
          <div class="vip-info-item" v-if="userInfo.vip_expire_at">
            <span class="label">到期时间</span>
            <span class="value">{{ userInfo.vip_expire_at }}</span>
          </div>
          <div class="vip-info-item">
            <span class="label">剩余天数</span>
            <span class="value">{{ userInfo.remaining_days || 0 }} 天</span>
          </div>
          <div class="vip-tips" v-if="!userInfo.is_vip">
            <p>会员已过期，请使用卡密充值续费</p>
            <p class="tips-desc">回复"充值 卡密"即可续费</p>
          </div>
          <button class="close-btn" @click="showVipInfo = false">关闭</button>
        </div>
      </div>

      <!-- Messages -->
      <div class="messages" ref="messagesContainer">
        <!-- Welcome -->
        <div class="welcome" v-if="messages.length === 0">
          <div class="welcome-icon">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20ZM12.88 11.03C12.59 10.73 12.34 10.44 12.17 10.16C12 9.88 11.92 9.57 11.92 9.22C11.92 8.58 12.13 8.05 12.55 7.64C12.97 7.22 13.53 7 14.22 7C14.91 7 15.47 7.22 15.89 7.64C16.31 8.05 16.52 8.58 16.52 9.22C16.52 9.57 16.44 9.88 16.27 10.16C16.1 10.44 15.85 10.73 15.56 11.03L12 14.5V17H13.5V15.09L16.42 12.17C17.02 11.56 17.52 10.79 17.52 9.22C17.52 7.65 16.22 6 14.22 6C12.22 6 10.92 7.65 10.92 9.22C10.92 10.79 11.42 11.56 12.02 12.17L12.88 11.03Z" fill="currentColor"/>
            </svg>
          </div>
          <h2>欢迎使用 AI智能刷步系统</h2>
          <p>简单对话，自动刷步</p>

          <!-- 功能卡片 -->
          <div class="feature-cards">
            <div class="feature-card">
              <span class="card-icon">🏃</span>
              <h4>刷步数</h4>
              <p>说"刷50000步"</p>
            </div>
            <div class="feature-card">
              <span class="card-icon">⏰</span>
              <h4>定时任务</h4>
              <p>说"每天9点前完成50000步"</p>
            </div>
            <div class="feature-card">
              <span class="card-icon">💳</span>
              <h4>充值续费</h4>
              <p>说"充值 卡密"</p>
            </div>
          </div>

          <div class="quick-actions">
            <button class="quick-btn primary" @click="inputText = '我要刷步'; sendMessage()">
              <span>🏃</span> 开始使用
            </button>
          </div>
        </div>

        <!-- Message List -->
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message', msg.role]"
        >
          <div class="message-avatar">
            <span v-if="msg.role === 'user'">我</span>
            <svg v-else viewBox="0 0 24 24" fill="none">
              <path d="M13.5 5.5C14.594 5.5 15.5 4.594 15.5 3.5C15.5 2.406 14.594 1.5 13.5 1.5C12.406 1.5 11.5 2.406 11.5 3.5C11.5 4.594 12.406 5.5 13.5 5.5Z" fill="currentColor"/>
              <path d="M9.89 19.38L10.89 15L13 17V23H15V15.5L12.89 13.5L13.5 10.5C14.79 12 16.79 13 19 13V11C17.09 11 15.5 10 14.69 8.58L13.69 7C13.29 6.38 12.69 6 12 6C11.69 6 11.5 6.08 11.19 6.19L6 8.28V13H8V9.58L9.79 8.88L8.19 17L3.29 16L2.89 18L9.89 19.38Z" fill="currentColor"/>
            </svg>
          </div>
          <div class="message-content">
            <p v-html="formatMessage(msg.content)"></p>
            <!-- Images -->
            <div v-if="msg.images && msg.images.length" class="images">
              <div v-for="(img, i) in msg.images" :key="i" class="image-item">
                <p class="image-label">{{ img.type === 'captcha' ? '请输入验证码' : '扫码绑定微信' }}</p>
                <img :src="img.data.startsWith('data:') ? img.data : 'data:image/png;base64,' + img.data" alt="image" />
              </div>
            </div>
          </div>
        </div>

        <!-- Typing -->
        <div v-if="loading" class="message assistant">
          <div class="message-avatar">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M13.5 5.5C14.594 5.5 15.5 4.594 15.5 3.5C15.5 2.406 14.594 1.5 13.5 1.5C12.406 1.5 11.5 2.406 11.5 3.5C11.5 4.594 12.406 5.5 13.5 5.5Z" fill="currentColor"/>
              <path d="M9.89 19.38L10.89 15L13 17V23H15V15.5L12.89 13.5L13.5 10.5C14.79 12 16.79 13 19 13V11C17.09 11 15.5 10 14.69 8.58L13.69 7C13.29 6.38 12.69 6 12 6C11.69 6 11.5 6.08 11.19 6.19L6 8.28V13H8V9.58L9.79 8.88L8.19 17L3.29 16L2.89 18L9.89 19.38Z" fill="currentColor"/>
            </svg>
          </div>
          <div class="message-content typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="input-area">
        <input
          v-model="inputText"
          type="text"
          placeholder="输入消息... (如: 刷50000步)"
          @keyup.enter="sendMessage"
          :disabled="loading"
        />
        <button class="send-btn" @click="sendMessage" :disabled="loading || !inputText.trim()">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M2.01 21L23 12L2.01 3L2 10L17 12L2 14L2.01 21Z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Chat',
  data() {
    return {
      userKey: '',
      messages: [],
      inputText: '',
      loading: false,
      userInfo: {
        is_vip: false,
        remaining_days: 0,
        vip_expire_at: null
      },
      showVipInfo: false
    }
  },
  mounted() {
    this.userKey = localStorage.getItem('userKey')
    if (!this.userKey) {
      this.$router.push('/')
      return
    }
    this.loadUserInfo()
  },
  methods: {
    async loadUserInfo() {
      try {
        const res = await axios.get('/api/user/info', {
          params: { user_key: this.userKey }
        })
        if (res.data.success) {
          this.userInfo = res.data.data
        }
      } catch (error) {
        console.error('加载用户信息失败:', error)
      }
    },

    formatMessage(text) {
      return text.replace(/\n/g, '<br>')
    },

    async sendMessage() {
      if (!this.inputText.trim() || this.loading) return

      const userMessage = this.inputText.trim()
      this.inputText = ''

      // Add user message
      this.messages.push({ role: 'user', content: userMessage })
      this.scrollToBottom()

      this.loading = true
      try {
        const res = await axios.post('/api/chat', {
          user_key: this.userKey,
          message: userMessage
        })

        // Add assistant message
        this.messages.push({
          role: 'assistant',
          content: res.data.reply,
          images: res.data.images || []
        })

        // 刷新用户信息
        this.loadUserInfo()
      } catch (error) {
        this.messages.push({
          role: 'assistant',
          content: '网络异常，请稍后重试'
        })
      } finally {
        this.loading = false
        this.scrollToBottom()
      }
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    },

    logout() {
      localStorage.removeItem('userKey')
      this.$router.push('/')
    }
  }
}
</script>

<style scoped>
.chat-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.chat-container {
  width: 100%;
  max-width: 480px;
  height: calc(100vh - 40px);
  max-height: 850px;
  background: #fff;
  border-radius: 24px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

/* Header */
.chat-header {
  padding: 14px 18px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  width: 36px;
  height: 36px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-icon svg {
  width: 20px;
  height: 20px;
  color: white;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title h1 {
  font-size: 16px;
  font-weight: 600;
  color: white;
  margin: 0;
}

.status-dot {
  width: 6px;
  height: 6px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.8);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.vip-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.vip-badge.active {
  background: rgba(255, 215, 0, 0.3);
  color: #ffd700;
}

.vip-badge.expired {
  background: rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.8);
}

.logout-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.1);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.logout-btn svg {
  width: 18px;
  height: 18px;
  color: white;
}

/* VIP Modal */
.vip-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.vip-modal-content {
  background: white;
  border-radius: 16px;
  padding: 24px;
  width: 300px;
  text-align: center;
}

.vip-modal-content h3 {
  font-size: 18px;
  margin-bottom: 20px;
  color: #333;
}

.vip-info-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #eee;
}

.vip-info-item .label {
  color: #666;
}

.vip-info-item .value {
  font-weight: 500;
  color: #333;
}

.vip-info-item .value.active {
  color: #17bf63;
}

.vip-tips {
  margin-top: 16px;
  padding: 12px;
  background: #fff3cd;
  border-radius: 8px;
}

.vip-tips p {
  color: #856404;
  font-size: 13px;
  margin: 0;
}

.vip-tips .tips-desc {
  margin-top: 4px;
  font-size: 12px;
}

.close-btn {
  margin-top: 20px;
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 14px;
  cursor: pointer;
}

/* Messages */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f8f9fa;
}

.welcome {
  text-align: center;
  padding: 30px 20px;
}

.welcome-icon {
  width: 70px;
  height: 70px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.welcome-icon svg {
  width: 36px;
  height: 36px;
  color: white;
}

.welcome h2 {
  font-size: 22px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 6px;
}

.welcome > p {
  font-size: 14px;
  color: #666;
  margin-bottom: 20px;
}

.feature-cards {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.feature-card {
  flex: 1;
  background: white;
  border-radius: 12px;
  padding: 14px 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.card-icon {
  font-size: 24px;
  display: block;
  margin-bottom: 8px;
}

.feature-card h4 {
  font-size: 13px;
  color: #333;
  margin-bottom: 4px;
}

.feature-card p {
  font-size: 11px;
  color: #888;
}

.quick-actions {
  display: flex;
  justify-content: center;
}

.quick-btn {
  padding: 12px 28px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.quick-btn.primary {
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.quick-btn:hover {
  transform: scale(1.02);
}

/* Message */
.message {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
}

.message.user .message-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message.assistant .message-avatar {
  background: #e8e8e8;
}

.message.assistant .message-avatar svg {
  width: 18px;
  height: 18px;
  color: #666;
}

.message-content {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
}

.message.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
  background: white;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.message-content p {
  margin: 0;
}

/* Images */
.images {
  margin-top: 10px;
}

.image-item {
  text-align: center;
}

.image-label {
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
}

.message.user .image-label {
  color: rgba(255, 255, 255, 0.8);
}

.image-item img {
  max-width: 180px;
  border-radius: 10px;
  border: 1px solid #eee;
}


/* Typing */
.message-content.typing {
  display: flex;
  gap: 4px;
  padding: 16px;
}

.message-content.typing span {
  width: 6px;
  height: 6px;
  background: #999;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.message-content.typing span:nth-child(1) { animation-delay: -0.32s; }
.message-content.typing span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* Input */
.input-area {
  padding: 14px 18px;
  background: white;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
}

.input-area input {
  flex: 1;
  padding: 12px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  font-size: 14px;
  background: #fafafa;
  transition: all 0.2s;
}

.input-area input:focus {
  outline: none;
  border-color: #667eea;
  background: white;
}

.send-btn {
  width: 46px;
  height: 46px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-btn svg {
  width: 20px;
  height: 20px;
}
</style>
