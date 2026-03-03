// pages/vip/vip.js
const api = require('../../utils/api')

Page({
  data: {
    packages: [],
    selectedPackage: null,
    loading: true,
    paying: false
  },

  onLoad() {
    this.loadPackages()
  },

  onShow() {
    this.loadPackages()
  },

  async loadPackages() {
    try {
      const res = await api.request('/packages', 'GET', {})
      if (res.success) {
        this.setData({
          packages: res.data || [],
          loading: false
        })
      }
    } catch (e) {
      console.error('加载套餐失败', e)
      this.setData({ loading: false })
    }
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
