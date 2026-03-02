// pages/chat/chat.js
const api = require('../../utils/api')

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false,
    scrollToView: ''
  },

  onLoad() {
    // 添加欢迎消息
    this.setData({
      messages: [{
        role: 'assistant',
        content: '您好！我是AI刷步助手。\n\n您可以说：\n• "我要刷步" - 注册账号\n• "刷50000步" - 刷步\n• "每天50000步" - 设置定时任务\n• "我的定时任务" - 查看任务详情\n• "会员状态" - 查看会员'
      }]
    })
  },

  // 输入框变化
  onInput(e) {
    this.setData({
      inputText: e.detail.value
    })
  },

  // 发送消息
  async sendMessage() {
    const text = this.data.inputText.trim()
    if (!text || this.data.loading) return

    // 添加用户消息
    const messages = [...this.data.messages, { role: 'user', content: text }]
    this.setData({
      messages,
      inputText: '',
      loading: true
    })

    this.scrollToBottom()

    try {
      const res = await api.chat(text)

      // 添加助手回复
      const newMessages = [...this.data.messages, {
        role: 'assistant',
        content: res.reply || '抱歉，出现了一些问题，请稍后再试。',
        images: res.images || []
      }]

      this.setData({
        messages: newMessages,
        loading: false
      })

      this.scrollToBottom()
    } catch (e) {
      console.error('发送消息失败', e)
      this.setData({
        messages: [...this.data.messages, {
          role: 'assistant',
          content: '网络错误，请稍后再试。'
        }],
        loading: false
      })
    }
  },

  // 预览图片
  previewImage(e) {
    const src = e.currentTarget.dataset.src
    wx.previewImage({
      current: src,
      urls: [src]
    })
  },

  // 滚动到底部
  scrollToBottom() {
    this.setData({
      scrollToView: 'bottom'
    })
  },

  // 快捷操作
  quickAction(e) {
    const action = e.currentTarget.dataset.action
    this.setData({ inputText: action }, () => {
      this.sendMessage()
    })
  }
})
