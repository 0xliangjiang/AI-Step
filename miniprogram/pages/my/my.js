// pages/my/my.js
const api = require('../../utils/api')

function parseDateTime(value) {
  if (!value) return null
  return new Date(value.replace(/-/g, '/'))
}

Page({
  data: {
    userInfo: null,
    userProfile: null,
    avatarText: '未',
    hasProfile: false,
    vipExpireAt: null,
    remainingDays: 0,
    isVip: false,
    isLoggedIn: false,
    loading: true
    // 广告相关 - 暂时隐藏
    // adRewardDays: 1,
    // adDailyLimit: 3,
    // adDailyCount: 0,
    // adCanWatch: false
  },

  onLoad() {
    this.syncLoginState()
    this.loadUserInfo()
    // this.loadAdConfig()
  },

  onShow() {
    this.syncLoginState()
    this.loadUserInfo()
    // this.loadAdStatus()
  },

  syncLoginState() {
    const app = getApp()
    const userProfile = app.globalData.userProfile || wx.getStorageSync('userProfile') || null
    const isLoggedIn = !!(app.globalData.openid || wx.getStorageSync('openid'))
    const hasProfile = !!(userProfile && (userProfile.nickName || userProfile.avatarUrl))
    const avatarText = isLoggedIn
      ? ((userProfile && userProfile.nickName) ? userProfile.nickName.charAt(0) : '微')
      : '未'

    this.setData({
      userProfile,
      isLoggedIn,
      hasProfile,
      avatarText
    })
  },

  async loadUserInfo() {
    if (!api.isLoggedIn()) {
      this.setData({
        userInfo: null,
        vipExpireAt: null,
        isVip: false,
        remainingDays: 0,
        loading: false,
        isLoggedIn: false
      })
      return
    }

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
            nickName: data.nickname || (this.data.userProfile && this.data.userProfile.nickName) || '',
            avatarUrl: data.avatar_url || (this.data.userProfile && this.data.userProfile.avatarUrl) || ''
          },
          vipExpireAt: data.vip_expire_at,
          isVip,
          remainingDays,
          loading: false,
          isLoggedIn: true,
          hasProfile: !!(data.nickname || data.avatar_url || (this.data.userProfile && (this.data.userProfile.nickName || this.data.userProfile.avatarUrl))),
          avatarText: data.nickname ? data.nickname.charAt(0) : this.data.avatarText
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
  //   if (!api.isLoggedIn()) {
  //     this.setData({
  //       adDailyCount: 0,
  //       adCanWatch: false
  //     })
  //     return
  //   }
  //
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

  async handleLogin() {
    const app = getApp()

    try {
      wx.showLoading({ title: '登录中...' })
      await app.loginWithWechat()
      wx.hideLoading()
      this.syncLoginState()
      await this.loadUserInfo()
      wx.showToast({
        title: this.data.isLoggedIn ? '资料已同步' : '登录成功',
        icon: 'success'
      })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({
        title: e.message || '登录失败',
        icon: 'none'
      })
    }
  },

  handleLogout() {
    const app = getApp()

    wx.showModal({
      title: '退出登录',
      content: '退出后需要重新授权登录，确定继续？',
      success: ({ confirm }) => {
        if (!confirm) return

        app.logout()
        this.setData({
          userInfo: null,
          userProfile: null,
          avatarText: '未',
          vipExpireAt: null,
          remainingDays: 0,
          isVip: false,
          isLoggedIn: false
        })

        wx.showToast({
          title: '已退出登录',
          icon: 'success'
        })
      }
    })
  },

  // 观看广告 - 暂时隐藏
  // watchAd() {
  //   if (!api.isLoggedIn()) {
  //     wx.showToast({
  //       title: '请先登录',
  //       icon: 'none'
  //     })
  //     return
  //   }
  //
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

  // 关于我们
  aboutUs() {
    wx.showModal({
      title: '关于我们',
      content: '运动AI助手 - 您的运动数据伙伴\n\n版本：1.0.0',
      showCancel: false
    })
  },

  // 去开通会员
  goVip() {
    if (!api.isLoggedIn()) {
      wx.showToast({
        title: '请先登录',
        icon: 'none'
      })
      return
    }

    wx.navigateTo({
      url: '/pages/vip/vip'
    })
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadUserInfo().then(() => {
      wx.stopPullDownRefresh()
    })
  }
})
