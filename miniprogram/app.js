// app.js
const { mergeUserProfile } = require('./utils/profile')

const API_BASE_URLS = {
  // 微信开发者工具 / 开发版
  develop: 'https://aistep.discordbot.cn',
  // 正式版
  release: 'https://aistep.discordbot.cn'
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
    // 小程序广告配置
    adConfig: {
      rewardedVideoAdUnitId: 'adunit-xxxxxxxxxxxxxxxx'
    },
    // 用户信息
    userInfo: null,
    userProfile: null,
    openid: null,
    vipExpireAt: null,
    publicConfig: {
      reviewMode: false
    }
  },

  async onLaunch() {
    console.log('[App] 当前API地址:', this.globalData.baseUrl)
    const cachedProfile = wx.getStorageSync('userProfile') || null
    this.globalData.userProfile = cachedProfile ? mergeUserProfile(cachedProfile, null) : null
    await this.loadPublicConfig()
    // 检查登录状态
    this.checkLogin()
  },

  loadPublicConfig() {
    return new Promise((resolve) => {
      wx.request({
        url: `${this.globalData.baseUrl}${this.globalData.apiPrefix}/public/config`,
        method: 'GET',
        success: (res) => {
          const reviewMode = !!(res.data && res.data.success && res.data.data && res.data.data.review_mode)
          this.globalData.publicConfig = { reviewMode }
          resolve(this.globalData.publicConfig)
        },
        fail: () => {
          this.globalData.publicConfig = { reviewMode: false }
          resolve(this.globalData.publicConfig)
        }
      })
    })
  },

  isReviewMode() {
    return !!(this.globalData.publicConfig && this.globalData.publicConfig.reviewMode)
  },

  // 检查登录状态
  checkLogin() {
    const openid = wx.getStorageSync('openid')
    if (openid) {
      this.globalData.openid = openid
      this.getUserInfo()
    }
  },

  // 微信登录并获取用户资料
  loginWithWechat() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (loginRes) => {
          if (!loginRes.code) {
            reject(new Error('获取微信登录凭证失败'))
            return
          }

          wx.request({
            url: `${this.globalData.baseUrl}${this.globalData.apiPrefix}/user/wxlogin`,
            method: 'POST',
            data: {
              code: loginRes.code
            },
            success: (res) => {
              if (!res.data.success || !res.data.openid) {
                reject(new Error(res.data.message || '登录失败'))
                return
              }

              const cachedProfile = wx.getStorageSync('userProfile') || null
              const mergedProfile = cachedProfile ? mergeUserProfile(cachedProfile, null) : null

              this.globalData.openid = res.data.openid
              this.globalData.userProfile = mergedProfile
              this.globalData.userInfo = {
                ...(this.globalData.userInfo || {}),
                nickname: mergedProfile ? mergedProfile.nickName : '',
                avatar_url: mergedProfile ? mergedProfile.avatarUrl : ''
              }
              wx.setStorageSync('openid', res.data.openid)
              this.getUserInfo()
              resolve({
                openid: res.data.openid,
                userProfile: mergedProfile
              })
            },
            fail: () => reject(new Error('登录请求失败'))
          })
        },
        fail: () => reject(new Error('微信登录失败'))
      })
    })
  },

  logout() {
    this.globalData.openid = null
    this.globalData.userInfo = null
    this.globalData.userProfile = null
    this.globalData.vipExpireAt = null
    wx.removeStorageSync('openid')
    wx.removeStorageSync('userProfile')
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
          const mergedProfile = mergeUserProfile(this.globalData.userProfile, res.data.data)
          this.globalData.userProfile = mergedProfile
          wx.setStorageSync('userProfile', mergedProfile)
          this.globalData.vipExpireAt = res.data.data.vip_expire_at
        }
      }
    })
  }
})
