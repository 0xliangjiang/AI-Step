// utils/api.js
const app = getApp()

// API 前缀
const API_PREFIX = '/api'

/**
 * 封装请求方法
 */
function request(url, method, data) {
  return new Promise((resolve, reject) => {
    // 添加 openid 到请求参数
    const openid = app.globalData.openid || wx.getStorageSync('openid')
    if (openid) {
      data.user_key = openid
    }

    wx.request({
      url: `${app.globalData.baseUrl}${API_PREFIX}${url}`,
      method: method,
      data: data,
      header: {
        'content-type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // 未登录，重新登录
          app.login()
          reject(new Error('请先登录'))
        } else {
          reject(new Error(res.data.message || '请求失败'))
        }
      },
      fail: (err) => {
        reject(new Error('网络错误'))
      }
    })
  })
}

/**
 * 用户登录
 */
function wxLogin(code) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.baseUrl}${API_PREFIX}/user/wxlogin`,
      method: 'POST',
      data: { code },
      success: (res) => {
        if (res.data.success) {
          resolve(res.data)
        } else {
          reject(new Error(res.data.message || '登录失败'))
        }
      },
      fail: reject
    })
  })
}

/**
 * 获取用户信息
 */
function getUserInfo() {
  return request('/user/info', 'GET', {})
}

/**
 * 发送聊天消息
 */
function chat(message) {
  return request('/chat', 'POST', { message })
}

/**
 * 检查VIP状态
 */
function checkVip() {
  return request('/user/vip', 'GET', {})
}

function isLoggedIn() {
  return !!(app.globalData.openid || wx.getStorageSync('openid'))
}

module.exports = {
  request,
  wxLogin,
  getUserInfo,
  chat,
  checkVip,
  isLoggedIn
}
