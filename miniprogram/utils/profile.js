function normalizeAvatarUrl(value, options = {}) {
  const { allowLocalTemp = true } = options

  if (typeof value !== 'string') return ''

  const trimmed = value.trim()
  if (!trimmed || trimmed === 'null' || trimmed === 'undefined' || trimmed === '[object Object]') {
    return ''
  }

  if (/^https?:\/\//i.test(trimmed) || /^cloud:\/\//i.test(trimmed) || /^data:image\//i.test(trimmed)) {
    return trimmed
  }

  if (allowLocalTemp && trimmed.startsWith('wxfile://')) {
    return trimmed
  }

  return ''
}

function normalizeNickname(value, fallback = '微信用户') {
  if (typeof value !== 'string') return fallback

  const trimmed = value.trim()
  return trimmed || fallback
}

function getAvatarText(nickname, fallback = '微') {
  const normalized = normalizeNickname(nickname, '')
  return normalized ? normalized.charAt(0) : fallback
}

function mergeUserProfile(cachedProfile, serverProfile) {
  const cachedNickname = normalizeNickname(
    cachedProfile && (cachedProfile.nickName || cachedProfile.nickname),
    ''
  )
  const serverNickname = normalizeNickname(
    serverProfile && (serverProfile.nickName || serverProfile.nickname),
    ''
  )
  const cachedAvatarUrl = normalizeAvatarUrl(
    cachedProfile && (cachedProfile.avatarUrl || cachedProfile.avatar_url),
    { allowLocalTemp: true }
  )
  const serverAvatarUrl = normalizeAvatarUrl(
    serverProfile && (serverProfile.avatarUrl || serverProfile.avatar_url),
    { allowLocalTemp: false }
  )

  return {
    nickName: serverNickname || cachedNickname || '',
    avatarUrl: cachedAvatarUrl || serverAvatarUrl || ''
  }
}

function resolveDisplayAvatarUrl() {
  for (let i = 0; i < arguments.length; i += 1) {
    const normalized = normalizeAvatarUrl(arguments[i], { allowLocalTemp: true })
    if (normalized) return normalized
  }
  return ''
}

module.exports = {
  normalizeAvatarUrl,
  normalizeNickname,
  getAvatarText,
  mergeUserProfile,
  resolveDisplayAvatarUrl
}
