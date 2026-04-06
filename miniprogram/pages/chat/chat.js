// pages/chat/chat.js
const api = require('../../utils/api')

// 运动类型配置（根据微信官方文档）
// 单位: number(个), distance(米), time(分钟), calorie(卡路里)
const SPORT_TYPES = [
  // 1000系列：time/calorie
  { id: 1001, name: '锻炼', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 1002, name: '体能训练', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 1003, name: '功能性训练', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  // 2000系列：time/calorie
  { id: 2001, name: '瑜伽', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 2002, name: '钓鱼', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 2003, name: '广场舞', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 2004, name: '踢足球', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 2005, name: '打篮球', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 2006, name: '打羽毛球', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 2007, name: '打乒乓球', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  { id: 2008, name: '打网球', units: [{ key: 'time', label: '分钟' }, { key: 'calorie', label: '卡路里' }] },
  // 3000系列：time/distance/calorie
  { id: 3001, name: '跑步', units: [{ key: 'time', label: '分钟' }, { key: 'distance', label: '米' }, { key: 'calorie', label: '卡路里' }] },
  { id: 3002, name: '登山', units: [{ key: 'time', label: '分钟' }, { key: 'distance', label: '米' }, { key: 'calorie', label: '卡路里' }] },
  { id: 3003, name: '骑车', units: [{ key: 'time', label: '分钟' }, { key: 'distance', label: '米' }, { key: 'calorie', label: '卡路里' }] },
  { id: 3004, name: '游泳', units: [{ key: 'time', label: '分钟' }, { key: 'distance', label: '米' }, { key: 'calorie', label: '卡路里' }] },
  { id: 3005, name: '滑雪', units: [{ key: 'time', label: '分钟' }, { key: 'distance', label: '米' }, { key: 'calorie', label: '卡路里' }] },
  // 4000系列：number/calorie
  { id: 4001, name: '跳绳', units: [{ key: 'number', label: '个' }, { key: 'calorie', label: '卡路里' }] },
  { id: 4002, name: '俯卧撑', units: [{ key: 'number', label: '个' }, { key: 'calorie', label: '卡路里' }] },
  { id: 4003, name: '深蹲', units: [{ key: 'number', label: '个' }, { key: 'calorie', label: '卡路里' }] }
]

// 运动名称到类型的映射（用于自然语言解析）
const SPORT_NAME_MAP = {
  '跑步': 3001, '跑': 3001, '跑步机': 3001,
  '登山': 3002, '爬山': 3002, '徒步': 3002,
  '骑车': 3003, '骑行': 3003, '自行车': 3003, '单车': 3003,
  '游泳': 3004, '泳': 3004,
  '滑雪': 3005,
  '瑜伽': 2001,
  '钓鱼': 2002,
  '广场舞': 2003, '跳舞': 2003,
  '足球': 2004, '踢足球': 2004,
  '篮球': 2005, '打篮球': 2005,
  '羽毛球': 2006, '打羽毛球': 2006,
  '乒乓球': 2007, '打乒乓球': 2007,
  '网球': 2008, '打网球': 2008,
  '跳绳': 4001,
  '俯卧撑': 4002,
  '深蹲': 4003,
  '锻炼': 1001, '健身': 1001,
  '体能训练': 1002,
  '功能性训练': 1003
}

// 单位关键词映射
const UNIT_KEYWORD_MAP = {
  '公里': { key: 'distance', factor: 1000 },  // 公里转米
  '千米': { key: 'distance', factor: 1000 },
  '米': { key: 'distance', factor: 1 },
  '步': { key: 'distance', factor: 0.7 },     // 步数转米（约0.7米/步）
  '分钟': { key: 'time', factor: 1 },
  '小时': { key: 'time', factor: 60 },        // 小时转分钟
  '个': { key: 'number', factor: 1 },
  '次': { key: 'number', factor: 1 },
  '卡路里': { key: 'calorie', factor: 1 },
  '千卡': { key: 'calorie', factor: 1000 }
}

// 解析自然语言运动描述
function parseSportText(text) {
  // 匹配模式: 分享/记录 + 运动类型 + 数值 + 单位
  // 例如: "分享跑步5公里", "记录游泳30分钟", "跳绳100个"

  const shareKeywords = ['分享', '记录', '上传', '同步', '提交']

  // 检查是否包含分享关键词
  const hasShareKeyword = shareKeywords.some(k => text.includes(k))
  if (!hasShareKeyword) return null

  // 尝试匹配运动类型
  let matchedSportId = null
  let matchedSportName = null
  for (const [name, id] of Object.entries(SPORT_NAME_MAP)) {
    if (text.includes(name)) {
      matchedSportId = id
      matchedSportName = name
      break
    }
  }

  if (!matchedSportId) return null

  // 尝试匹配数值和单位
  // 匹配数字（包括小数）
  const numberMatch = text.match(/(\d+(?:\.\d+)?)/)
  if (!numberMatch) return null

  const rawValue = parseFloat(numberMatch[1])

  // 尝试匹配单位
  let matchedUnit = null
  let finalValue = rawValue

  for (const [keyword, config] of Object.entries(UNIT_KEYWORD_MAP)) {
    if (text.includes(keyword)) {
      matchedUnit = config.key
      finalValue = Math.round(rawValue * config.factor)
      break
    }
  }

  // 如果没匹配到单位，根据运动类型推断默认单位
  if (!matchedUnit) {
    const sportType = SPORT_TYPES.find(t => t.id === matchedSportId)
    if (sportType) {
      // 跑步、登山、骑车、游泳、滑雪默认用距离
      if ([3001, 3002, 3003, 3004, 3005].includes(matchedSportId)) {
        matchedUnit = 'distance'
        finalValue = Math.round(rawValue * 1000) // 默认假设是公里
      } else if ([4001, 4002, 4003].includes(matchedSportId)) {
        matchedUnit = 'number'
      } else {
        matchedUnit = 'time' // 其他运动默认用时间
      }
    }
  }

  return {
    sportId: matchedSportId,
    sportName: matchedSportName,
    unit: matchedUnit,
    value: finalValue
  }
}

Page({
  data: {
    messages: [],
    inputText: '',
    loading: false,
    scrollToView: '',
    userProfile: null,
    avatarText: '微',
    // 分享相关
    showShareModal: false,
    shareSteps: 0,
    sportTypes: SPORT_TYPES,
    selectedSportIndex: 0,
    selectedUnitIndex: 0,
    inputValue: ''
  },

  onLoad() {
    const app = getApp()
    if (app.isReviewMode()) {
      wx.showToast({
        title: '当前版本暂未开放',
        icon: 'none'
      })
      setTimeout(() => {
        wx.switchTab({
          url: '/pages/index/index'
        })
      }, 800)
      return
    }

    this.syncUserProfile()
    // 添加欢迎消息
    this.setData({
      messages: [{
        role: 'assistant',
        content: '您好，欢迎使用运动助手。\n\n您可以在这里：\n• 记录运动数据\n• 查看健康趋势\n• 获取运动建议\n• 制定运动计划\n• 同步运动数据\n\n同步示例：\n• 同步跑步5公里\n• 记录游泳30分钟\n• 记录跳绳100个\n\n请输入您的需求。'
      }]
    })
  },

  onShow() {
    this.syncUserProfile()
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

  // 输入框变化
  onInput(e) {
    this.setData({
      inputText: e.detail.value
    })
  },

  // 发送消息
  async sendMessage() {
    const text = this.data.inputText.trim()
    if (!text || this.data.loading) return

    // 检查是否是"分享运动状态"等模糊分享意图（无具体数据）
    const generalShareKeywords = ['分享运动状态', '分享运动', '分享到微信运动', '上传运动', '同步运动']
    if (generalShareKeywords.some(k => text.includes(k))) {
      this.openShareModal()
      this.setData({ inputText: '' })
      return
    }

    // 检查是否是分享运动的自然语言（含具体数据）
    const sportParsed = parseSportText(text)
    if (sportParsed) {
      console.log('解析到运动分享请求:', sportParsed)
      this.setData({ inputText: '' })
      // 直接弹出分享弹窗
      this.showShareModalFromParsed(sportParsed)
      return
    }

    // 添加用户消息
    const messages = [...this.data.messages, { role: 'user', content: text }]
    this.setData({
      messages,
      inputText: '',
      loading: true
    })

    this.scrollToBottom()

    try {
      const res = await api.chat(text)

      console.log('API响应:', res)
      if (res.function_result) {
        console.log('function_result:', res.function_result)
      }

      const fallbackErrorMessage =
        (res.function_result && (res.function_result.message || res.function_result.debug_message)) ||
        ''
      const displayReply =
        (!res.success && res.reply === '系统异常，请联系QQ:188177020处理' && fallbackErrorMessage)
          ? `系统异常\n${fallbackErrorMessage}`
          : (res.reply || '抱歉，出现了一些问题，请稍后再试。')

      // 添加助手回复
      const newMessages = [...this.data.messages, {
        role: 'assistant',
        content: displayReply,
        images: res.images || []
      }]

      this.setData({
        messages: newMessages,
        loading: false
      })

      this.scrollToBottom()

      // 检测数据同步成功，自动弹出弹窗
      this.checkBrushSuccess(res.reply, res.function_result)

    } catch (e) {
      console.error('发送消息失败', e)
      this.setData({
        messages: [...this.data.messages, {
          role: 'assistant',
          content: '网络错误，请稍后再试。'
        }],
        loading: false
      })
    }
  },

  // 根据解析结果弹出分享弹窗
  showShareModalFromParsed(parsed) {
    const { sportId, sportName, unit, value } = parsed

    // 找到运动类型索引
    const sportIndex = SPORT_TYPES.findIndex(t => t.id === sportId)
    if (sportIndex < 0) {
      wx.showToast({ title: '未找到运动类型', icon: 'none' })
      return
    }

    const sportType = SPORT_TYPES[sportIndex]

    // 找到单位索引
    const unitIndex = sportType.units.findIndex(u => u.key === unit)
    if (unitIndex < 0) {
      // 如果该运动类型不支持该单位，使用第一个单位
      wx.showToast({
        title: `${sportName}不支持${unit === 'distance' ? '距离' : unit === 'time' ? '时间' : unit === 'number' ? '次数' : '卡路里'}单位`,
        icon: 'none'
      })
      return
    }

    this.setData({
      showShareModal: true,
      shareSteps: 0,
      inputValue: String(value),
      selectedSportIndex: sportIndex,
      selectedUnitIndex: unitIndex
    })
  },

  // 快捷按钮：直接弹出分享弹窗
  openShareModal() {
    this.setData({
      showShareModal: true,
      inputValue: '',
      selectedSportIndex: 0,
      selectedUnitIndex: 0
    })
  },

  // 检测数据同步完成
  checkBrushSuccess(reply, functionResult) {
    // 从 function_result 获取同步数据
    let steps = 0

    if (functionResult && functionResult.steps) {
      steps = functionResult.steps
    } else if (reply) {
      // 兼容从消息中提取
      const match = reply.match(/(\d+)\s*步/)
      if (match && reply.includes('完成')) {
        steps = parseInt(match[1])
      }
    }

    if (steps > 0) {
      // 默认选择跑步(3001)，将步数转换为距离（一步约0.7米）
      const distance = Math.round(steps * 0.7)
      // 找到跑步的索引
      const runIndex = SPORT_TYPES.findIndex(t => t.id === 3001)
      // 找到距离单位的索引
      const runType = SPORT_TYPES[runIndex]
      const distanceUnitIndex = runType.units.findIndex(u => u.key === 'distance')

      this.setData({
        showShareModal: true,
        shareSteps: steps,
        inputValue: String(distance),
        selectedSportIndex: runIndex >= 0 ? runIndex : 0,
        selectedUnitIndex: distanceUnitIndex >= 0 ? distanceUnitIndex : 0
      })
    }
  },

  // 选择运动类型
  onSportTypeChange(e) {
    const index = e.detail.value

    // 找到默认是 time 的单位，否则选第一个
    const sportType = SPORT_TYPES[index]
    let unitIndex = sportType.units.findIndex(u => u.key === 'time')
    if (unitIndex < 0) unitIndex = 0

    this.setData({
      selectedSportIndex: index,
      selectedUnitIndex: unitIndex,
      inputValue: ''
    })
  },

  // 选择单位
  onUnitChange(e) {
    this.setData({
      selectedUnitIndex: e.detail.value
    })
  },

  // 输入数值变化
  onValueInput(e) {
    this.setData({
      inputValue: e.detail.value
    })
  },

  // 分享到微信运动
  async shareToWeRun() {
    console.log('shareToWeRun 被调用')
    const { selectedSportIndex, selectedUnitIndex, inputValue, sportTypes } = this.data
    const selectedType = sportTypes[selectedSportIndex]
    const selectedUnit = selectedType.units[selectedUnitIndex]
    const value = parseInt(inputValue) || 0

    console.log('分享参数:', { typeId: selectedType.id, unit: selectedUnit.key, value })

    // 根据单位验证数值范围
    const limits = {
      number: { min: 1, max: 10000 },
      distance: { min: 1, max: 100000 },
      time: { min: 1, max: 1440 },
      calorie: { min: 1, max: 10000 }
    }
    const limit = limits[selectedUnit.key] || { min: 1, max: 10000 }

    if (value < limit.min || value > limit.max) {
      wx.showToast({
        title: `数值范围: ${limit.min}-${limit.max}`,
        icon: 'none'
      })
      return
    }

    try {
      // 1. 先获取微信运动权限
      console.log('请求微信运动权限...')
      await wx.authorize({ scope: 'scope.werun' })
      console.log('微信运动权限授权成功')
    } catch (e) {
      console.error('微信运动权限授权失败:', e)
      const errMsg = e.errMsg || ''

      // 隐私API被禁止 - 需要在公众平台配置
      if (errMsg.includes('privacy api banned') || errMsg.includes('banned')) {
        wx.showModal({
          title: '功能暂不可用',
          content: '微信运动分享功能需要在小程序后台配置隐私协议并申请接口权限后才能使用。\n\n请联系开发者处理。',
          showCancel: false
        })
        return
      }

      // 用户拒绝授权，引导去设置页面
      if (errMsg.includes('auth deny')) {
        wx.showModal({
          title: '需要授权',
          content: '请授权微信运动权限，以便分享运动数据',
          confirmText: '去授权',
          success: (res) => {
            if (res.confirm) {
              wx.openSetting()
            }
          }
        })
      } else {
        // 其他错误也显示提示
        wx.showToast({
          title: errMsg || '授权失败',
          icon: 'none'
        })
      }
      return
    }

    try {
      wx.showLoading({ title: '分享中...' })

      // 2. 调用分享接口
      // 根据选择的单位动态设置字段名 (number/distance/time/calorie)
      const recordData = {
        typeId: selectedType.id
      }
      recordData[selectedUnit.key] = value

      console.log('调用 wx.shareToWeRun:', recordData)
      await wx.shareToWeRun({
        recordList: [recordData]
      })
      console.log('wx.shareToWeRun 调用成功')

      wx.hideLoading()
      wx.showToast({
        title: '分享成功',
        icon: 'success'
      })

      this.setData({ showShareModal: false })

    } catch (e) {
      wx.hideLoading()
      console.error('分享到微信运动失败', e)

      // 判断是否是接口未开通
      if (e.errMsg && e.errMsg.includes('not support')) {
        wx.showToast({
          title: '当前版本不支持',
          icon: 'none'
        })
      } else {
        wx.showToast({
          title: e.errMsg || '分享失败',
          icon: 'none'
        })
      }
    }
  },

  // 关闭分享弹窗
  closeShareModal() {
    this.setData({ showShareModal: false })
  },

  // 预览图片
  previewImage(e) {
    const src = e.currentTarget.dataset.src
    wx.previewImage({
      current: src,
      urls: [src]
    })
  },

  // 滚动到底部
  scrollToBottom() {
    this.setData({
      scrollToView: 'bottom'
    })
  },

  // 快捷操作
  quickAction(e) {
    const action = e.currentTarget.dataset.action
    this.setData({ inputText: action }, () => {
      this.sendMessage()
    })
  }
})
