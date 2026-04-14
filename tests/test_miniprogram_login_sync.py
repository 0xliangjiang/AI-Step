import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MiniProgramLoginSyncTests(unittest.TestCase):
    def test_login_flow_syncs_cached_profile_and_membership_state(self):
        app_js = (ROOT / 'miniprogram' / 'app.js').read_text(encoding='utf-8')
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')
        my_js = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.js').read_text(encoding='utf-8')

        self.assertIn("nickname: mergedProfile ? mergedProfile.nickName : ''", app_js)
        self.assertIn("avatar_url: mergedProfile ? mergedProfile.avatarUrl : ''", app_js)
        self.assertIn('return this.getUserInfo()', app_js)
        self.assertIn('return new Promise((resolve, reject) => {', app_js)

        self.assertIn('applyUserInfo(data)', index_js)
        self.assertIn('const cachedUserInfo = app.globalData.userInfo', index_js)
        self.assertIn('this.applyUserInfo(cachedUserInfo)', index_js)

        self.assertIn('applyUserInfo(data)', my_js)
        self.assertIn('const cachedUserInfo = app.globalData.userInfo', my_js)
        self.assertIn('this.applyUserInfo(cachedUserInfo)', my_js)

    def test_first_login_guides_profile_completion(self):
        index_wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')
        my_wxml = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.wxml').read_text(encoding='utf-8')

        self.assertIn('showProfileGuide', index_js)
        self.assertIn('maybePromptProfileCompletion()', index_js)
        self.assertIn('goMyProfile()', index_js)
        self.assertIn('资料补充后可更快识别你的记录', index_wxml)
        self.assertIn('去完善', index_wxml)
        self.assertIn('继续完善资料', my_wxml)
        self.assertIn('补充头像和昵称后，首页展示会更完整。', my_wxml)

    def test_homepage_trial_days_and_vip_packages_have_stable_fallbacks(self):
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')
        index_wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')
        vip_js = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.js').read_text(encoding='utf-8')
        vip_wxml = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.wxml').read_text(encoding='utf-8')

        self.assertIn("const remainingDays = typeof data.remaining_days === 'number'", index_js)
        self.assertIn("remainingDays > 0 ? remainingDays + '天' : '已结束'", index_wxml)

        self.assertIn("const PACKAGE_CACHE_KEY = 'vipPackagesCache'", vip_js)
        self.assertIn("const PACKAGE_ENDPOINTS = ['/membership/options', '/vip/packages', '/packages']", vip_js)
        self.assertIn('wx.getStorageSync(PACKAGE_CACHE_KEY)', vip_js)
        self.assertIn('wx.setStorageSync(PACKAGE_CACHE_KEY, packages)', vip_js)
        self.assertIn('usingCachedPackages', vip_js)
        self.assertIn('refreshPackages()', vip_js)
        self.assertIn('if (!res.success) {', vip_js)
        self.assertNotIn("throw new Error(res.message || '套餐暂时不可用')", vip_js)
        self.assertIn('套餐暂时没加载出来', vip_wxml)
        self.assertIn('重新加载', vip_wxml)

    def test_homepage_no_longer_auto_prompts_login_before_browsing(self):
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')
        index_wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')

        self.assertNotIn('checkShowLoginModal()', index_js)
        self.assertNotIn('showLoginModal', index_js)
        self.assertNotIn('handleLogin()', index_js)
        self.assertNotIn('skipLogin()', index_js)
        self.assertNotIn('loginLoading', index_js)
        self.assertNotIn('loginBenefits', index_js)
        self.assertNotIn('login-modal-mask', index_wxml)
        self.assertNotIn('微信一键登录', index_wxml)

    def test_chat_page_only_enforces_login_in_production_mode(self):
        chat_js = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.js').read_text(encoding='utf-8')
        chat_wxml = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxml').read_text(encoding='utf-8')
        chat_wxss = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxss').read_text(encoding='utf-8')

        self.assertIn('showLoginGate: false', chat_js)
        self.assertIn('loginLoading: false', chat_js)
        self.assertIn('checkChatLoginGate()', chat_js)
        self.assertIn('handleGateLogin()', chat_js)
        self.assertIn('if (app.isReviewMode()) {', chat_js)
        self.assertIn('showLoginGate: !app.globalData.openid', chat_js)
        self.assertNotIn('当前版本暂未开放', chat_js)
        self.assertNotIn("wx.switchTab({\n          url: '/pages/index/index'\n        })", chat_js)

        self.assertIn('wx:if="{{showLoginGate}}"', chat_wxml)
        self.assertIn('bindtap="handleGateLogin"', chat_wxml)
        self.assertIn('登录后可继续查看记录、同步数据和保存历史', chat_wxml)
        self.assertIn('立即登录', chat_wxml)

        self.assertIn('.login-gate-mask', chat_wxss)
        self.assertIn('.login-gate-card', chat_wxss)
        self.assertIn('.login-gate-button', chat_wxss)


if __name__ == '__main__':
    unittest.main()
