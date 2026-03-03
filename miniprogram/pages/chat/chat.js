// pages/chat/chat.js
const api = require('../../utils/api')

// 运动类型配置
const SPORT_TYPES = [
  { id: 1001, name: '步数', unit: '步', valueKey: 'steps' },
  { id: 1002, name: '跑步', unit: '米', valueKey: 'distance' },
  { id: 1003, name: '骑行', unit: '米', valueKey: 'distance' },
  { id: 1004, name: '游泳', unit: '米', valueKey: 'distance' },
  { id: 1005, name: '健走', unit: '步', valueKey: 'steps' },
  { id: 1006, name: '健身', unit: '分钟', valueKey: 'duration' },
  { id: 1007, name: '瑜伽', unit: '分钟', valueKey: 'duration' },
  { id: 1008, name: '跳绳', unit: '次', valueKey: 'count' },
  { id: 1009, name: '椭圆机', unit: '分钟', valueKey: 'duration' },
  { id: 1010, name: '划船机', unit: '分钟', valueKey: 'duration' }
]

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false,
    scrollToView: '',
    // 分享相关
    showShareModal: false,
    shareSteps: 0,
    sportTypes: SPORT_TYPES,
    selectedSportIndex: 0,
    inputValue: ''
  },

  onLoad() {
    // 添加欢迎消息
    this.setData({
      messages: [{
        role: 'assistant',
        content: '您好！我是智问AI助手，很高兴为您服务。\n\n我可以帮您：\n• 回答各类问题\n• 提供专业建议\n• 进行日常对话\n• 处理生活事务\n\n请问有什么可以帮您的？'
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

      // 调试：打印返回的图片数据
      console.log('API响应:', res)
      console.log('图片数据:', res.images)

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

      // 检测刷步成功，弹出分享提示
      this.checkBrushSuccess(res.reply)

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

  // 检测刷步成功
  checkBrushSuccess(reply) {
    if (!reply) return

    // 匹配刷步成功的消息，提取步数
    const match = reply.match(/刷步成功.*?(\d+)\s*步/)
    if (match) {
      const steps = parseInt(match[1])
      this.setData({
        showShareModal: true,
        shareSteps: steps,
        inputValue: String(steps),
        selectedSportIndex: 0  // 默认选择步数
      })
    }
  },

  // 选择运动类型
  onSportTypeChange(e) {
    const index = e.detail.value
    const selectedType = SPORT_TYPES[index]

    this.setData({
      selectedSportIndex: index
    })

    // 根据运动类型自动转换数值
    this.convertValue(this.data.shareSteps, selectedType)
  },

  // 转换数值
  convertValue(steps, sportType) {
    let value = steps

    switch (sportType.valueKey) {
      case 'steps':
        // 步数保持不变
        value = steps
        break
      case 'distance':
        // 距离：假设一步约0.7米
        value = Math.round(steps * 0.7)
        break
      case 'duration':
        // 时长：假设每分钟100步
        value = Math.round(steps / 100)
        break
      case 'count':
        // 次数：保持不变
        value = steps
        break
    }

    this.setData({
      inputValue: String(value)
    })
  },

  // 输入数值变化
  onValueInput(e) {
    this.setData({
      inputValue: e.detail.value
    })
  },

  // 分享到微信运动
  async shareToWeRun() {
    const { selectedSportIndex, inputValue, sportTypes } = this.data
    const selectedType = sportTypes[selectedSportIndex]
    const value = parseInt(inputValue) || 0

    if (value <= 0) {
      wx.showToast({
        title: '请输入有效的数值',
        icon: 'none'
      })
      return
    }

    try {
      // 1. 先获取微信运动权限
      await wx.authorize({ scope: 'scope.werun' })
    } catch (e) {
      // 用户拒绝授权，引导去设置页面
      if (e.errMsg && e.errMsg.includes('auth deny')) {
        wx.showModal({
          title: '需要授权',
          content: '请授权微信运动权限，以便分享运动数据',
          confirmText: '去授权',
          success: (res) => {
            if (res.confirm) {
              wx.openSetting()
            }
          }
        })
      }
      return
    }

    try {
      wx.showLoading({ title: '分享中...' })

      // 2. 调用分享接口
      await wx.shareToWeRun({
        recordList: [{
          typeId: selectedType.id,
          time: Math.floor(Date.now() / 1000),
          value: value
        }]
      })

      wx.hideLoading()
      wx.showToast({
        title: '分享成功',
        icon: 'success'
      })

      this.setData({ showShareModal: false })

    } catch (e) {
      wx.hideLoading()
      console.error('分享到微信运动失败', e)

      // 判断是否是接口未开通
      if (e.errMsg && e.errMsg.includes('not support')) {
        wx.showToast({
          title: '当前版本不支持',
          icon: 'none'
        })
      } else {
        wx.showToast({
          title: e.errMsg || '分享失败',
          icon: 'none'
        })
      }
    }
  },

  // 关闭分享弹窗
  closeShareModal() {
    this.setData({ showShareModal: false })
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
