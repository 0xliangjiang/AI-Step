// utils/api.js

// API 前缀
const API_PREFIX = '/api'

function getAppInstance() {
  try {
    return getApp() || null
  } catch (error) {
    return null
  }
}

function getBaseUrl() {
  const app = getAppInstance()
  const globalData = (app && app.globalData) || {}
  return globalData.baseUrl || ''
}

/**
 * 封装请求方法
 */
function request(url, method, data) {
  return new Promise((resolve, reject) => {
    const app = getAppInstance()
    const globalData = (app && app.globalData) || {}
    // 添加 openid 到请求参数
    const openid = globalData.openid || wx.getStorageSync('openid')
    if (openid) {
      data.user_key = openid
    }

    wx.request({
      url: `${getBaseUrl()}${API_PREFIX}${url}`,
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
          if (app && typeof app.loginWithWechat === 'function') {
            app.loginWithWechat().catch(() => {})
          }
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
      url: `${getBaseUrl()}${API_PREFIX}/user/wxlogin`,
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

function updateUserProfile(data) {
  return request('/user/profile', 'POST', data)
}

function getSyncStatus() {
  return request('/user/sync-status', 'GET', {})
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
  const app = getAppInstance()
  const globalData = (app && app.globalData) || {}
  return !!(globalData.openid || wx.getStorageSync('openid'))
}

module.exports = {
  request,
  wxLogin,
  getUserInfo,
  getSyncStatus,
  updateUserProfile,
  chat,
  checkVip,
  isLoggedIn
}
