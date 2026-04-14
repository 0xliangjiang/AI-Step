const api = require('../../utils/api')

function formatStatusDetail(log) {
  if (!log) {
    return '最近一次状态记录暂未生成'
  }

  const prefix = log.mode_text ? `${log.mode_text} · ` : ''
  return `${prefix}${log.detail || '最近一次状态记录已更新'}`
}

Page({
  data: {
    loading: true,
    hasTask: false,
    statusText: '状态更新中',
    lastResultText: '未设置',
    targetSteps: 0,
    timeRange: '--',
    currentProgress: '0/0',
    lastSuccessAt: '',
    lastAttemptAt: '',
    lastDetail: '',
    consecutiveFailures: 0,
    nextSyncAt: '',
    logs: []
  },

  onLoad() {
    this.loadSyncStatus()
  },

  onPullDownRefresh() {
    this.loadSyncStatus().finally(() => {
      wx.stopPullDownRefresh()
    })
  },

  async loadSyncStatus() {
    this.setData({ loading: true })

    try {
      const res = await api.getSyncStatus()
      if (!res.success || !res.data) {
        wx.showToast({
          title: res.message || '暂时无法获取状态',
          icon: 'none'
        })
        this.setData({ loading: false })
        return
      }

      const logs = (res.data.logs || []).map((item) => ({
        ...item,
        displayDetail: formatStatusDetail(item)
      }))

      this.setData({
        loading: false,
        hasTask: !!res.data.has_task,
        statusText: res.data.status_text || '状态更新中',
        lastResultText: res.data.last_result_text || '状态更新中',
        targetSteps: res.data.target_steps || 0,
        timeRange: res.data.time_range || '--',
        currentProgress: res.data.current_progress || '0/0',
        lastSuccessAt: res.data.last_success_at || '',
        lastAttemptAt: res.data.last_attempt_at || '',
        lastDetail: res.data.last_detail || '最近一次状态记录已更新',
        consecutiveFailures: res.data.consecutive_failures || 0,
        nextSyncAt: res.data.next_sync_at || '',
        logs
      })
    } catch (error) {
      wx.showToast({
        title: '状态加载失败',
        icon: 'none'
      })
      this.setData({ loading: false })
    }
  }
})
