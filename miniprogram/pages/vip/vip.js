// pages/vip/vip.js
const api = require('../../utils/api')

const PACKAGE_CACHE_KEY = 'vipPackagesCache'
const PACKAGE_ENDPOINTS = ['/vip/packages', '/packages']

Page({
  data: {
    packages: [],
    selectedPackage: null,
    loading: true,
    paying: false,
    usingCachedPackages: false,
    loadError: ''
  },

  onLoad() {
    this.loadPackages()
  },

  onShow() {
    this.loadPackages()
  },

  async loadPackages() {
    if (this.loadingPackagesPromise) {
      return this.loadingPackagesPromise
    }

    const cachedPackages = wx.getStorageSync(PACKAGE_CACHE_KEY) || []
    if (cachedPackages.length && !this.data.packages.length) {
      this.applyPackages(cachedPackages, true)
    } else {
      this.setData({ loading: true, loadError: '' })
    }

    this.loadingPackagesPromise = this.fetchPackages(cachedPackages)
    return this.loadingPackagesPromise
  },

  async fetchPackages(cachedPackages) {
    try {
      const res = await this.requestPackages()
      if (!res.success) {
        this.showPackageFallback(cachedPackages, res.message || '套餐暂时没加载出来，请重新加载。')
        return
      }

      const packages = Array.isArray(res.data) ? res.data : []
      if (packages.length) {
        this.applyPackages(packages, false)
        wx.setStorageSync(PACKAGE_CACHE_KEY, packages)
        return
      }

      this.showPackageFallback(cachedPackages, '套餐暂时没加载出来，请重新加载。')
    } catch (e) {
      console.error('加载套餐失败', e)
      this.showPackageFallback(cachedPackages, '网络开小差了，请重新加载。')
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

  showPackageFallback(cachedPackages, message) {
    if (cachedPackages.length) {
      this.applyPackages(cachedPackages, true)
      this.setData({
        loadError: `${message} 先展示上次可用内容。`
      })
      return
    }

    this.setData({
      loading: false,
      loadError: message
    })
  },

  applyPackages(packages, usingCachedPackages) {
    const selectedPackageId = this.data.selectedPackage && this.data.selectedPackage.id
    const selectedPackage = packages.find((pkg) => pkg.id === selectedPackageId) || packages[0] || null

    this.setData({
      packages,
      selectedPackage,
      loading: false,
      usingCachedPackages,
      loadError: usingCachedPackages ? this.data.loadError : ''
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

  async createOrder() {
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

      // 调用微信支付
      const payParams = res.pay_params
      await wx.requestPayment({
        timeStamp: payParams.timeStamp,
        nonceStr: payParams.nonceStr,
        package: payParams.package,
        signType: payParams.signType,
        paySign: payParams.paySign
      })

      // 支付成功
      wx.showToast({ title: '支付成功', icon: 'success' })

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
