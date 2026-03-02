// pages/index/index.js
const api = require('../../utils/api')

Page({
  data: {
    userInfo: null,
    vipExpireAt: null,
    remainingDays: 0,
    isVip: false,
    loading: true
  },

  onLoad() {
    this.loadUserInfo()
  },

  onShow() {
    this.loadUserInfo()
  },

  // 加载用户信息
  async loadUserInfo() {
    try {
      const res = await api.getUserInfo()
      if (res.success) {
        const data = res.data
        const now = new Date()
        const expireAt = data.vip_expire_at ? new Date(data.vip_expire_at) : null
        const isVip = expireAt && expireAt > now
        const remainingDays = isVip ? Math.ceil((expireAt - now) / (1000 * 60 * 60 * 24)) : 0

        this.setData({
          userInfo: data,
          vipExpireAt: data.vip_expire_at,
          isVip,
          remainingDays,
          loading: false
        })
      }
    } catch (e) {
      console.error('获取用户信息失败', e)
      this.setData({ loading: false })
    }
  },

  // 去聊天页
  goChat() {
    wx.switchTab({
      url: '/pages/chat/chat'
    })
  },

  // 复制联系QQ
  copyQQ() {
    wx.setClipboardData({
      data: '188177020',
      success: () => {
        wx.showToast({ title: '已复制QQ号', icon: 'success' })
      }
    })
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadUserInfo().then(() => {
      wx.stopPullDownRefresh()
    })
  }
})
