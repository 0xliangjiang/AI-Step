// app.js
const API_BASE_URLS = {
  // 微信开发者工具 / 开发版
  develop: 'http://127.0.0.1:8000',
  // 体验版
  trial: 'https://api-staging.example.com',
  // 正式版
  release: 'https://api.example.com'
}

function resolveBaseUrl() {
  try {
    const accountInfo = wx.getAccountInfoSync()
    const envVersion = accountInfo?.miniProgram?.envVersion || 'release'
    return API_BASE_URLS[envVersion] || API_BASE_URLS.release
  } catch (error) {
    return API_BASE_URLS.release
  }
}

App({
  globalData: {
    // 后端API地址
    baseUrl: resolveBaseUrl(),
    // API 前缀
    apiPrefix: '/api',
    // 用户信息
    userInfo: null,
    openid: null,
    vipExpireAt: null
  },

  onLaunch() {
    console.log('[App] 当前API地址:', this.globalData.baseUrl)
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
            url: `${this.globalData.baseUrl}${this.globalData.apiPrefix}/user/wxlogin`,
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
      url: `${this.globalData.baseUrl}${this.globalData.apiPrefix}/user/info`,
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
