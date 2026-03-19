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
    vipExpireAt: null,
    remainingDays: 0,
    isVip: false,
    loading: true,
    // 广告相关
    adRewardDays: 1,
    adDailyLimit: 3,
    adDailyCount: 0,
    adCanWatch: false
  },

  onLoad() {
    this.syncUserProfile()
    this.loadUserInfo()
    this.loadAdConfig()
  },

  onShow() {
    this.syncUserProfile()
    this.loadUserInfo()
    this.loadAdStatus()
  },

  syncUserProfile() {
    const app = getApp()
    const userProfile = app.globalData.userProfile || wx.getStorageSync('userProfile') || null
    const avatarText = userProfile && userProfile.nickName
      ? userProfile.nickName.charAt(0)
      : '微'

    this.setData({
      userProfile,
      avatarText
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

  async loadAdConfig() {
    try {
      const res = await api.request('/user/ad-config', 'GET', {})
      if (res.success) {
        this.setData({
          adRewardDays: res.reward_days || 1,
          adDailyLimit: res.daily_limit || 3
        })
      }
    } catch (e) {
      console.error('获取广告配置失败', e)
    }
  },

  async loadAdStatus() {
    try {
      const res = await api.request('/user/ad-status', 'GET', {})
      if (res.success) {
        const canWatch = res.daily_count < res.daily_limit
        this.setData({
          adDailyCount: res.daily_count || 0,
          adCanWatch: canWatch
        })
      }
    } catch (e) {
      console.error('获取广告状态失败', e)
    }
  },

  // 去聊天页
  goChat() {
    wx.switchTab({
      url: '/pages/chat/chat'
    })
  },

  // 观看广告
  watchAd() {
    // 创建激励视频广告
    if (!this.rewardedVideoAd) {
      const app = getApp()
      const adUnitId = app.globalData.adConfig.rewardedVideoAdUnitId
      if (!adUnitId || adUnitId === 'adunit-xxxxxxxxxxxxxxxx') {
        wx.showToast({
          title: '广告位未配置',
          icon: 'none'
        })
        return
      }

      this.rewardedVideoAd = wx.createRewardedVideoAd({
        adUnitId
      })

      this.rewardedVideoAd.onClose((res) => {
        if (res && res.isEnded) {
          // 正常播放结束，发放奖励
          this.claimAdReward()
        } else {
          wx.showToast({
            title: '观看完整才能获得奖励',
            icon: 'none'
          })
        }
      })

      this.rewardedVideoAd.onError((err) => {
        console.error('广告加载失败', err)
        wx.showToast({
          title: '广告加载失败，请稍后重试',
          icon: 'none'
        })
      })
    }

    // 显示广告
    this.rewardedVideoAd.show().catch(() => {
      // 失败重试
      this.rewardedVideoAd.load().then(() => this.rewardedVideoAd.show())
    })
  },

  // 领取广告奖励
  async claimAdReward() {
    try {
      wx.showLoading({ title: '领取中...' })
      const res = await api.request('/user/watch-ad', 'POST', {})
      wx.hideLoading()

      if (res.success) {
        wx.showToast({
          title: `+${res.reward_days}天会员`,
          icon: 'success'
        })
        // 刷新用户信息和广告状态
        this.loadUserInfo()
        this.loadAdStatus()
      } else {
        wx.showToast({
          title: res.message || '领取失败',
          icon: 'none'
        })
      }
    } catch (e) {
      wx.hideLoading()
      wx.showToast({
        title: '网络错误',
        icon: 'none'
      })
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    Promise.all([
      this.loadUserInfo(),
      this.loadAdStatus()
    ]).then(() => {
      wx.stopPullDownRefresh()
    })
  }
})
