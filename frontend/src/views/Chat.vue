<template>
  <div class="chat-page">
    <div class="chat-container">
      <!-- Header -->
      <header class="chat-header">
        <div class="header-left">
          <div class="avatar">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2Z" fill="url(#gradient1)"/>
              <path d="M8 12H16M12 8V16" stroke="white" stroke-width="2" stroke-linecap="round"/>
              <defs>
                <linearGradient id="gradient1" x1="2" y1="2" x2="22" y2="22">
                  <stop stop-color="#6366f1"/>
                  <stop offset="1" stop-color="#8b5cf6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div class="header-info">
            <h1>智问AI助手</h1>
            <span class="status">
              <span class="dot"></span>
              在线
            </span>
          </div>
        </div>
        <div class="header-right">
          <div class="vip-tag" :class="{ active: userInfo.is_vip }" @click="showVipInfo = true">
            <span v-if="userInfo.is_vip">VIP {{ userInfo.remaining_days }}天</span>
            <span v-else>会员</span>
          </div>
          <button class="icon-btn" @click="logout" title="退出">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>
            </svg>
          </button>
        </div>
      </header>

      <!-- VIP弹窗 -->
      <div class="modal-overlay" v-if="showVipInfo" @click.self="showVipInfo = false">
        <div class="modal">
          <h3>会员信息</h3>
          <div class="info-row">
            <span>状态</span>
            <span :class="{ 'text-green': userInfo.is_vip }">
              {{ userInfo.is_vip ? '有效' : '已过期' }}
            </span>
          </div>
          <div class="info-row" v-if="userInfo.vip_expire_at">
            <span>到期时间</span>
            <span>{{ userInfo.vip_expire_at }}</span>
          </div>
          <div class="info-row">
            <span>剩余天数</span>
            <span>{{ userInfo.remaining_days || 0 }} 天</span>
          </div>
          <div class="tips" v-if="!userInfo.is_vip">
            会员已过期，请回复"充值 卡密"续费
          </div>
          <button class="modal-btn" @click="showVipInfo = false">关闭</button>
        </div>
      </div>

      <!-- Messages -->
      <div class="messages" ref="messagesContainer">
        <!-- Welcome -->
        <div class="welcome" v-if="messages.length === 0">
          <div class="welcome-avatar">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2Z" fill="url(#gradient2)"/>
              <path d="M8 12H16M12 8V16" stroke="white" stroke-width="2" stroke-linecap="round"/>
              <defs>
                <linearGradient id="gradient2" x1="2" y1="2" x2="22" y2="22">
                  <stop stop-color="#6366f1"/>
                  <stop offset="1" stop-color="#8b5cf6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h2>你好，我是智问AI助手</h2>
          <p>有什么可以帮助你的吗？</p>

          <div class="suggestions">
            <button class="suggestion-btn" @click="quickSend('你好')">
              <span>👋</span> 打个招呼
            </button>
            <button class="suggestion-btn" @click="quickSend('帮我写一首诗')">
              <span>✍️</span> 写首诗
            </button>
            <button class="suggestion-btn" @click="quickSend('讲个笑话')">
              <span>😄</span> 讲笑话
            </button>
            <button class="suggestion-btn" @click="quickSend('今天吃什么')">
              <span>🍜</span> 美食推荐
            </button>
          </div>
        </div>

        <!-- Message List -->
        <div v-for="(msg, index) in messages" :key="index" :class="['msg', msg.role]">
          <div class="msg-avatar">
            <span v-if="msg.role === 'user'">我</span>
            <svg v-else viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" fill="#6366f1"/>
              <path d="M8 12H16M12 8V16" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="msg-bubble">
            <p v-html="formatMessage(msg.content)"></p>
            <div v-if="msg.images && msg.images.length" class="msg-images">
              <div v-for="(img, i) in msg.images" :key="i" class="msg-image">
                <span class="img-label">{{ img.type === 'captcha' ? '请输入验证码' : '扫码绑定微信' }}</span>
                <img :src="img.data.startsWith('data:') ? img.data : 'data:image/png;base64,' + img.data" />
              </div>
            </div>
          </div>
        </div>

        <!-- Typing -->
        <div v-if="loading" class="msg assistant">
          <div class="msg-avatar">
            <svg viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" fill="#6366f1"/>
              <path d="M8 12H16M12 8V16" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="msg-bubble typing">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="input-bar">
        <input
          v-model="inputText"
          type="text"
          placeholder="输入消息..."
          @keyup.enter="sendMessage"
          :disabled="loading"
        />
        <button class="send-btn" @click="sendMessage" :disabled="loading || !inputText.trim()">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M22 2L11 13M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
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

    quickSend(text) {
      this.inputText = text
      this.sendMessage()
    },

    async sendMessage() {
      if (!this.inputText.trim() || this.loading) return

      const userMessage = this.inputText.trim()
      this.inputText = ''

      this.messages.push({ role: 'user', content: userMessage })
      this.scrollToBottom()

      this.loading = true
      try {
        const res = await axios.post('/api/chat', {
          user_key: this.userKey,
          message: userMessage
        })

        this.messages.push({
          role: 'assistant',
          content: res.data.reply,
          images: res.data.images || []
        })

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
  padding: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.chat-container {
  width: 100%;
  max-width: 420px;
  height: calc(100vh - 32px);
  max-height: 700px;
  background: #f7f8fc;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}

/* Header */
.chat-header {
  padding: 16px;
  background: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  overflow: hidden;
}

.avatar svg {
  width: 100%;
  height: 100%;
}

.header-info h1 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #10b981;
}

.dot {
  width: 8px;
  height: 8px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.9); }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.vip-tag {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  background: #f3f4f6;
  color: #6b7280;
  transition: all 0.2s;
}

.vip-tag.active {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #fff;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: #f3f4f6;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: #e5e7eb;
  color: #374151;
}

.icon-btn svg {
  width: 18px;
  height: 18px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px);
}

.modal {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  width: 280px;
  text-align: center;
}

.modal h3 {
  font-size: 18px;
  margin-bottom: 20px;
  color: #1a1a2e;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 14px;
}

.info-row span:first-child {
  color: #6b7280;
}

.info-row span:last-child {
  color: #1a1a2e;
  font-weight: 500;
}

.text-green {
  color: #10b981 !important;
}

.tips {
  margin-top: 16px;
  padding: 12px;
  background: #fef3c7;
  border-radius: 8px;
  font-size: 13px;
  color: #92400e;
}

.modal-btn {
  margin-top: 20px;
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

/* Messages */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.welcome {
  text-align: center;
  padding: 40px 20px;
}

.welcome-avatar {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
}

.welcome-avatar svg {
  width: 100%;
  height: 100%;
}

.welcome h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.welcome > p {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 32px;
}

.suggestions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.suggestion-btn {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s;
}

.suggestion-btn:hover {
  border-color: #6366f1;
  color: #6366f1;
  background: #f5f3ff;
}

/* Message */
.msg {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.msg.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
}

.msg.user .msg-avatar {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
}

.msg.assistant .msg-avatar {
  background: #fff;
}

.msg-avatar svg {
  width: 24px;
  height: 24px;
}

.msg-bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
}

.msg.user .msg-bubble {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.msg.assistant .msg-bubble {
  background: #fff;
  color: #1a1a2e;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.msg-bubble p {
  margin: 0;
}

.msg-images {
  margin-top: 12px;
}

.msg-image {
  text-align: center;
}

.img-label {
  display: block;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 8px;
}

.msg-image img {
  max-width: 160px;
  border-radius: 8px;
}

/* Typing */
.msg-bubble.typing {
  display: flex;
  gap: 4px;
  padding: 16px;
}

.msg-bubble.typing span {
  width: 8px;
  height: 8px;
  background: #9ca3af;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.msg-bubble.typing span:nth-child(1) { animation-delay: -0.32s; }
.msg-bubble.typing span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* Input */
.input-bar {
  padding: 12px 16px;
  background: #fff;
  border-top: 1px solid #eee;
  display: flex;
  gap: 10px;
}

.input-bar input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  font-size: 14px;
  background: #f9fafb;
  transition: all 0.2s;
}

.input-bar input:focus {
  outline: none;
  border-color: #6366f1;
  background: #fff;
}

.send-btn {
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
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
