// app.js
App({
  globalData: {
    // 后端API地址
    baseUrl: 'https://your-domain.com/api',
    // 用户信息
    userInfo: null,
    openid: null,
    vipExpireAt: null
  },

  onLaunch() {
    // 检查登录状态
    this.checkLogin()
  },

  // 检查登录状态
  checkLogin() {
    const openid = wx.getStorageSync('openid')
    if (openid) {
      this.globalData.openid = openid
      this.getUserInfo()
    } else {
      this.login()
    }
  },

  // 微信登录
  login() {
    wx.login({
      success: (res) => {
        if (res.code) {
          // 发送 code 到后端换取 openid
          wx.request({
            url: `${this.globalData.baseUrl}/user/wxlogin`,
            method: 'POST',
            data: { code: res.code },
            success: (res) => {
              if (res.data.success) {
                this.globalData.openid = res.data.openid
                wx.setStorageSync('openid', res.data.openid)
                this.getUserInfo()
              }
            }
          })
        }
      }
    })
  },

  // 获取用户信息
  getUserInfo() {
    if (!this.globalData.openid) return

    wx.request({
      url: `${this.globalData.baseUrl}/user/info`,
      method: 'GET',
      data: { user_key: this.globalData.openid },
      success: (res) => {
        if (res.data.success) {
          this.globalData.userInfo = res.data.data
          this.globalData.vipExpireAt = res.data.data.vip_expire_at
        }
      }
    })
  }
})
