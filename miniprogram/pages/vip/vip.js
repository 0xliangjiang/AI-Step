// pages/vip/vip.js
const api = require('../../utils/api')
const app = getApp()

const PACKAGE_ENDPOINTS = ['/membership/options', '/vip/packages', '/packages']
const PAYMENT_QUERY_MAX_ATTEMPTS = 4
const PAYMENT_QUERY_INTERVAL_MS = 1200

Page({
  data: {
    packages: [],
    selectedPackage: null,
    loading: true,
    paying: false,
    loadError: '',
    reviewMode: false
  },

  onLoad() {
    this.loadPackages()
  },

  onShow() {
    this.loadPackages()
  },

  async loadPackages() {
    this.setData({ reviewMode: app.isReviewMode() || app.isMembershipHidden() })
    if (this.data.reviewMode) {
      this.setData({
        packages: [],
        selectedPackage: null,
        loading: false,
        paying: false,
        loadError: ''
      })
      return Promise.resolve()
    }

    if (this.loadingPackagesPromise) {
      return this.loadingPackagesPromise
    }

    this.setData({ loading: true, loadError: '' })

    this.loadingPackagesPromise = this.fetchPackages()
    return this.loadingPackagesPromise
  },

  async fetchPackages() {
    try {
      const res = await this.requestPackages()
      if (!res.success) {
        this.showPackageUnavailable(res.message || '套餐暂时没加载出来，请重新加载。')
        return
      }

      const packages = Array.isArray(res.data) ? res.data : []
      if (packages.length) {
        this.applyPackages(packages)
        return
      }

      this.showPackageUnavailable('套餐暂时没加载出来，请重新加载。')
    } catch (e) {
      console.error('加载套餐失败', e)
      this.showPackageUnavailable('网络开小差了，请重新加载。')
    } finally {
      this.loadingPackagesPromise = null
    }
  },

  async requestPackages() {
    let lastError = null

    for (const endpoint of PACKAGE_ENDPOINTS) {
      try {
        return await api.request(endpoint, 'GET', {})
      } catch (error) {
        lastError = error
      }
    }

    throw lastError || new Error('网络开小差了，请重新加载。')
  },

  showPackageUnavailable(message) {
    wx.removeStorageSync('vipPackagesCache')
    this.setData({
      packages: [],
      selectedPackage: null,
      loading: false,
      loadError: message
    })
  },

  applyPackages(packages) {
    const selectedPackageId = this.data.selectedPackage && this.data.selectedPackage.id
    const selectedPackage = packages.find((pkg) => pkg.id === selectedPackageId) || packages[0] || null

    this.setData({
      packages,
      selectedPackage,
      loading: false,
      loadError: ''
    })
  },

  refreshPackages() {
    this.setData({
      loading: true,
      loadError: ''
    })
    this.loadingPackagesPromise = null
    this.loadPackages()
  },

  selectPackage(e) {
    const id = e.currentTarget.dataset.id
    const pkg = this.data.packages.find(p => p.id === id)
    this.setData({ selectedPackage: pkg })
  },

  wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms))
  },

  async confirmPaymentSettled(orderNo) {
    if (!orderNo) {
      return false
    }

    for (let attempt = 0; attempt < PAYMENT_QUERY_MAX_ATTEMPTS; attempt += 1) {
      if (attempt > 0) {
        await this.wait(PAYMENT_QUERY_INTERVAL_MS)
      }

      const queryRes = await api.request(`/pay/query/${orderNo}`, 'GET', {})
      if (queryRes.success && queryRes.status === 'paid') {
        return true
      }
    }

    return false
  },

  async createOrder() {
    if (this.data.reviewMode) {
      wx.showToast({ title: '当前版本暂未开放', icon: 'none' })
      return
    }

    const pkg = this.data.selectedPackage
    if (!pkg) {
      wx.showToast({ title: '请选择套餐', icon: 'none' })
      return
    }

    this.setData({ paying: true })

    try {
      // 创建订单
      const res = await api.request('/pay/create', 'POST', {
        package_id: pkg.id
      })

      if (!res.success) {
        wx.showToast({ title: res.message || '下单失败', icon: 'none' })
        this.setData({ paying: false })
        return
      }

      const orderNo = res.order_no
      // 调用微信支付
      const payParams = res.pay_params
      await wx.requestPayment({
        timeStamp: payParams.timeStamp,
        nonceStr: payParams.nonceStr,
        package: payParams.package,
        signType: payParams.signType,
        paySign: payParams.paySign
      })

      const settled = await this.confirmPaymentSettled(orderNo)
      if (settled) {
        wx.showToast({ title: '支付已到账', icon: 'success' })
      } else {
        wx.showToast({ title: '支付处理中', icon: 'none' })
      }

      // 刷新页面
      setTimeout(() => {
        wx.switchTab({ url: '/pages/my/my' })
      }, 1500)

    } catch (e) {
      console.error('支付失败', e)
      if (e.errMsg && e.errMsg.includes('cancel')) {
        wx.showToast({ title: '已取消支付', icon: 'none' })
      } else {
        wx.showToast({ title: '支付失败', icon: 'none' })
      }
    } finally {
      this.setData({ paying: false })
    }
  },

  formatPrice(price) {
    // 分转元
    return (price / 100).toFixed(2)
  }
})
