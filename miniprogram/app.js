// app.js
const API_BASE_URLS = {
  // 微信开发者工具 / 开发版
  develop: 'http://localhost:8000',
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
    // 小程序广告配置
    adConfig: {
      rewardedVideoAdUnitId: 'adunit-xxxxxxxxxxxxxxxx'
    },
    // 用户信息
    userInfo: null,
    userProfile: null,
    openid: null,
    vipExpireAt: null
  },

  onLaunch() {
    console.log('[App] 当前API地址:', this.globalData.baseUrl)
    this.globalData.userProfile = wx.getStorageSync('userProfile') || null
    // 检查登录状态
    this.checkLogin()
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
      wx.getUserProfile({
        desc: '用于展示微信头像和昵称',
        success: (profileRes) => {
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
                  code: loginRes.code,
                  nickname: profileRes.userInfo.nickName || '',
                  avatar_url: profileRes.userInfo.avatarUrl || ''
                },
                success: (res) => {
                  if (!res.data.success || !res.data.openid) {
                    reject(new Error(res.data.message || '登录失败'))
                    return
                  }

                  const userProfile = {
                    nickName: profileRes.userInfo.nickName || '微信用户',
                    avatarUrl: profileRes.userInfo.avatarUrl || '',
                    gender: profileRes.userInfo.gender || 0
                  }

                  this.globalData.openid = res.data.openid
                  this.globalData.userProfile = userProfile
                  this.globalData.userInfo = {
                    ...(this.globalData.userInfo || {}),
                    nickname: userProfile.nickName,
                    avatar_url: userProfile.avatarUrl
                  }
                  wx.setStorageSync('openid', res.data.openid)
                  wx.setStorageSync('userProfile', userProfile)
                  this.getUserInfo()
                  resolve({
                    openid: res.data.openid,
                    userProfile
                  })
                },
                fail: () => reject(new Error('登录请求失败'))
              })
            },
            fail: () => reject(new Error('微信登录失败'))
          })
        },
        fail: () => reject(new Error('用户取消授权'))
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
          if (res.data.data.nickname || res.data.data.avatar_url) {
            const userProfile = {
              nickName: res.data.data.nickname || '微信用户',
              avatarUrl: res.data.data.avatar_url || ''
            }
            this.globalData.userProfile = userProfile
            wx.setStorageSync('userProfile', userProfile)
          }
          this.globalData.vipExpireAt = res.data.data.vip_expire_at
        }
      }
    })
  }
})
