// pages/index/index.js
const api = require('../../utils/api')
const { getAvatarText, mergeUserProfile, resolveDisplayAvatarUrl } = require('../../utils/profile')

function parseDateTime(value) {
  if (!value) return null
  return new Date(value.replace(/-/g, '/'))
}

Page({
  data: {
    userInfo: null,
    userProfile: null,
    avatarText: '微',
    displayAvatarUrl: '',
    hasProfile: false,
    greeting: '你好',
    vipExpireAt: null,
    remainingDays: 0,
    isVip: false,
    loading: true,
    reviewMode: false,
    showProfileGuide: false,
    
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
  },

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
    const rawProfile = app.globalData.userProfile || wx.getStorageSync('userProfile') || null
    const userProfile = rawProfile ? mergeUserProfile(rawProfile, null) : null
    const avatarText = getAvatarText(userProfile && userProfile.nickName, '微')

    this.setData({
      userProfile,
      avatarText,
      displayAvatarUrl: resolveDisplayAvatarUrl(userProfile && userProfile.avatarUrl),
      hasProfile: !!(userProfile && (userProfile.nickName || userProfile.avatarUrl)),
      greeting: this.getGreeting()
    })
  },

  applyUserInfo(data) {
    if (!data) return

    const now = new Date()
    const expireAt = parseDateTime(data.vip_expire_at)
    const isVip = expireAt && expireAt > now
    const remainingDays = typeof data.remaining_days === 'number'
      ? data.remaining_days
      : (isVip ? Math.ceil((expireAt - now) / (1000 * 60 * 60 * 24)) : 0)
    const userProfile = mergeUserProfile(this.data.userProfile, data)
    const avatarText = getAvatarText(userProfile.nickName, this.data.avatarText || '微')
    const displayAvatarUrl = resolveDisplayAvatarUrl(userProfile.avatarUrl)
    const hasProfile = !!(userProfile.nickName || displayAvatarUrl)
    const app = getApp()

    app.globalData.userInfo = data
    app.globalData.userProfile = userProfile
    app.globalData.vipExpireAt = data.vip_expire_at
    wx.setStorageSync('userProfile', userProfile)

    this.setData({
      userInfo: data,
      userProfile,
      avatarText,
      displayAvatarUrl,
      hasProfile,
      vipExpireAt: data.vip_expire_at,
      isVip,
      remainingDays,
      loading: false
    })
  },

  maybePromptProfileCompletion() {
    const app = getApp()
    const openid = app.globalData.openid || wx.getStorageSync('openid')
    if (!openid || this.data.hasProfile) return

    const guideKey = `profileGuideShown_${openid}`
    if (wx.getStorageSync(guideKey)) return

    wx.setStorageSync(guideKey, 1)
    this.setData({ showProfileGuide: true })
  },

  closeProfileGuide() {
    this.setData({ showProfileGuide: false })
  },

  goMyProfile() {
    this.setData({ showProfileGuide: false })
    wx.switchTab({
      url: '/pages/my/my'
    })
  },

  // 加载用户信息
  async loadUserInfo() {
    const app = getApp()
    const cachedUserInfo = app.globalData.userInfo
    if (cachedUserInfo) {
      this.applyUserInfo(cachedUserInfo)
    }

    try {
      const res = await api.getUserInfo()
      if (res.success) {
        this.applyUserInfo(res.data)
        this.maybePromptProfileCompletion()
      }
    } catch (e) {
      console.error('获取用户信息失败', e)
      if (!cachedUserInfo) {
        this.setData({ loading: false })
      }
    }
  },

  onAvatarError() {
    this.setData({
      displayAvatarUrl: ''
    })
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
