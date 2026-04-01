// pages/index/index.js
const api = require('../../utils/api')

function parseDateTime(value) {
  if (!value) return null
  return new Date(value.replace(/-/g, '/'))
}

Page({
  data: {
    userInfo: null,
    userProfile: null,
    avatarText: '微',
    greeting: '你好',
    vipExpireAt: null,
    remainingDays: 0,
    isVip: false,
    loading: true,
    reviewMode: false,
    // 登录弹窗
    showLoginModal: false,
    loginLoading: false,
    loginBenefits: [
      { icon: '🏃', text: '记录运动数据到微信运动' },
      { icon: '📊', text: '查看历史运动记录' },
      { icon: '🎯', text: '个性化运动建议' }
    ]
  },

  onLoad() {
    this.syncReviewMode()
    this.syncUserProfile()
    this.loadUserInfo()
  },

  onShow() {
    this.syncReviewMode()
    this.syncUserProfile()
    this.loadUserInfo()
    // 检查是否需要显示登录弹窗
    this.checkShowLoginModal()
  },

  // 检查是否需要显示登录弹窗
  checkShowLoginModal() {
    const app = getApp()
    const isLoggedIn = !!(app.globalData.openid || wx.getStorageSync('openid'))
    const hasSkippedLogin = wx.getStorageSync('hasSkippedLogin')

    // 未登录且没有跳过过登录，则显示弹窗
    if (!isLoggedIn && !hasSkippedLogin) {
      this.setData({ showLoginModal: true })
    }
  },

  // 处理登录
  async handleLogin() {
    const app = getApp()

    this.setData({ loginLoading: true })

    try {
      await app.loginWithWechat()
      this.setData({
        showLoginModal: false,
        loginLoading: false
      })
      this.syncUserProfile()
      await this.loadUserInfo()
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      })
    } catch (e) {
      this.setData({ loginLoading: false })
      wx.showToast({
        title: e.message || '登录失败',
        icon: 'none'
      })
    }
  },

  // 跳过登录
  skipLogin() {
    wx.setStorageSync('hasSkippedLogin', true)
    this.setData({ showLoginModal: false })
  },

  // 阻止触摸穿透
  preventTouchMove() {},

  syncReviewMode() {
    const app = getApp()
    this.setData({
      reviewMode: app.isReviewMode(),
      greeting: this.getGreeting()
    })
  },

  getGreeting() {
    const hour = new Date().getHours()
    if (hour < 6) return '夜深了'
    if (hour < 9) return '早上好'
    if (hour < 12) return '上午好'
    if (hour < 14) return '中午好'
    if (hour < 18) return '下午好'
    if (hour < 22) return '晚上好'
    return '夜深了'
  },

  syncUserProfile() {
    const app = getApp()
    const userProfile = app.globalData.userProfile || wx.getStorageSync('userProfile') || null
    const avatarText = userProfile && userProfile.nickName
      ? userProfile.nickName.charAt(0)
      : '微'

    this.setData({
      userProfile,
      avatarText,
      greeting: this.getGreeting()
    })
  },

  // 加载用户信息
  async loadUserInfo() {
    try {
      const res = await api.getUserInfo()
      if (res.success) {
        const data = res.data
        const now = new Date()
        const expireAt = parseDateTime(data.vip_expire_at)
        const isVip = expireAt && expireAt > now
        const remainingDays = isVip ? Math.ceil((expireAt - now) / (1000 * 60 * 60 * 24)) : 0

        this.setData({
          userInfo: data,
          userProfile: {
            nickName: data.nickname || (this.data.userProfile && this.data.userProfile.nickName) || '微信用户',
            avatarUrl: data.avatar_url || (this.data.userProfile && this.data.userProfile.avatarUrl) || ''
          },
          avatarText: data.nickname ? data.nickname.charAt(0) : this.data.avatarText,
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

  // 广告相关方法 - 暂时隐藏
  // async loadAdConfig() {
  //   try {
  //     const res = await api.request('/user/ad-config', 'GET', {})
  //     if (res.success) {
  //       this.setData({
  //         adRewardDays: res.reward_days || 1,
  //         adDailyLimit: res.daily_limit || 3
  //       })
  //     }
  //   } catch (e) {
  //     console.error('获取广告配置失败', e)
  //   }
  // },

  // async loadAdStatus() {
  //   try {
  //     const res = await api.request('/user/ad-status', 'GET', {})
  //     if (res.success) {
  //       const canWatch = res.daily_count < res.daily_limit
  //       this.setData({
  //         adDailyCount: res.daily_count || 0,
  //         adCanWatch: canWatch
  //       })
  //     }
  //   } catch (e) {
  //     console.error('获取广告状态失败', e)
  //   }
  // },

  // 去聊天页
  goChat() {
    if (this.data.reviewMode) {
      wx.showToast({
        title: '当前版本暂未开放',
        icon: 'none'
      })
      return
    }

    wx.switchTab({
      url: '/pages/chat/chat'
    })
  },

  // 观看广告 - 暂时隐藏
  // watchAd() {
  //   // 创建激励视频广告
  //   if (!this.rewardedVideoAd) {
  //     const app = getApp()
  //     const adUnitId = app.globalData.adConfig.rewardedVideoAdUnitId
  //     if (!adUnitId || adUnitId === 'adunit-xxxxxxxxxxxxxxxx') {
  //       wx.showToast({
  //         title: '广告位未配置',
  //         icon: 'none'
  //       })
  //       return
  //     }
  //
  //     this.rewardedVideoAd = wx.createRewardedVideoAd({
  //       adUnitId
  //     })
  //
  //     this.rewardedVideoAd.onClose((res) => {
  //       if (res && res.isEnded) {
  //         // 正常播放结束，发放奖励
  //         this.claimAdReward()
  //       } else {
  //         wx.showToast({
  //           title: '观看完整才能获得奖励',
  //           icon: 'none'
  //         })
  //       }
  //     })
  //
  //     this.rewardedVideoAd.onError((err) => {
  //       console.error('广告加载失败', err)
  //       wx.showToast({
  //         title: '广告加载失败，请稍后重试',
  //         icon: 'none'
  //       })
  //     })
  //   }
  //
  //   // 显示广告
  //   this.rewardedVideoAd.show().catch(() => {
  //     // 失败重试
  //     this.rewardedVideoAd.load().then(() => this.rewardedVideoAd.show())
  //   })
  // },

  // 领取广告奖励 - 暂时隐藏
  // async claimAdReward() {
  //   try {
  //     wx.showLoading({ title: '领取中...' })
  //     const res = await api.request('/user/watch-ad', 'POST', {})
  //     wx.hideLoading()
  //
  //     if (res.success) {
  //       wx.showToast({
  //         title: `+${res.reward_days}天会员`,
  //         icon: 'success'
  //       })
  //       // 刷新用户信息和广告状态
  //       this.loadUserInfo()
  //       this.loadAdStatus()
  //     } else {
  //       wx.showToast({
  //         title: res.message || '领取失败',
  //         icon: 'none'
  //       })
  //     }
  //   } catch (e) {
  //     wx.hideLoading()
  //     wx.showToast({
  //       title: '网络错误',
  //       icon: 'none'
  //     })
  //   }
  // },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadUserInfo().then(() => {
      wx.stopPullDownRefresh()
    })
  }
})
