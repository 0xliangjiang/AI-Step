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

    def test_homepage_trial_days_and_vip_packages_hide_when_unavailable(self):
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')
        index_wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')
        vip_js = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.js').read_text(encoding='utf-8')
        vip_wxml = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.wxml').read_text(encoding='utf-8')

        self.assertIn("const remainingDays = typeof data.remaining_days === 'number'", index_js)
        self.assertIn("remainingDays > 0 ? remainingDays + '天' : '已结束'", index_wxml)

        self.assertIn("const PACKAGE_ENDPOINTS = ['/membership/options', '/vip/packages', '/packages']", vip_js)
        self.assertIn("wx.removeStorageSync('vipPackagesCache')", vip_js)
        self.assertIn('refreshPackages()', vip_js)
        self.assertIn('if (!res.success) {', vip_js)
        self.assertNotIn("throw new Error(res.message || '套餐暂时不可用')", vip_js)
        self.assertNotIn('PACKAGE_CACHE_KEY', vip_js)
        self.assertNotIn('wx.getStorageSync(PACKAGE_CACHE_KEY)', vip_js)
        self.assertNotIn('wx.setStorageSync(PACKAGE_CACHE_KEY', vip_js)
        self.assertNotIn('usingCachedPackages', vip_js + vip_wxml)
        self.assertNotIn('showPackageFallback(cachedPackages', vip_js)
        self.assertNotIn('先展示上次可用内容', vip_js + vip_wxml)
        self.assertIn('套餐暂时没加载出来', vip_wxml)
        self.assertIn('重新加载', vip_wxml)
        self.assertIn('class="benefits" wx:if="{{!reviewMode && packages.length}}"', vip_wxml)
        self.assertIn('class="footer" wx:if="{{!reviewMode && packages.length}}"', vip_wxml)

    def test_payment_success_confirms_backend_settlement_before_navigating(self):
        vip_js = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.js').read_text(encoding='utf-8')

        self.assertIn("res.order_no", vip_js)
        self.assertIn("api.request(`/pay/query/${orderNo}`", vip_js)
        self.assertIn("queryRes.status === 'paid'", vip_js)
        self.assertIn("const orderNo = res.order_no", vip_js)
        self.assertIn("await this.confirmPaymentSettled(orderNo)", vip_js)
        self.assertIn("title: '支付已到账'", vip_js)
        self.assertIn("title: '支付处理中'", vip_js)

    def test_vip_page_hides_packages_and_payment_in_review_mode(self):
        vip_js = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.js').read_text(encoding='utf-8')
        vip_wxml = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.wxml').read_text(encoding='utf-8')

        self.assertIn('reviewMode: false', vip_js)
        self.assertIn('const app = getApp()', vip_js)
        self.assertIn('reviewMode: app.isReviewMode()', vip_js)
        self.assertIn('if (this.data.reviewMode) {', vip_js)
        self.assertIn('packages: []', vip_js)
        self.assertIn('selectedPackage: null', vip_js)
        self.assertIn('return Promise.resolve()', vip_js)
        self.assertIn("title: '当前版本暂未开放'", vip_js)

        self.assertIn('wx:if="{{reviewMode}}"', vip_wxml)
        self.assertIn('当前版本暂未开放此服务', vip_wxml)
        self.assertIn('wx:if="{{!reviewMode && packages.length}}"', vip_wxml)
        self.assertIn('wx:elif="{{!reviewMode && !loading}}"', vip_wxml)
        self.assertIn('wx:if="{{!reviewMode && packages.length}}"', vip_wxml)
        self.assertIn('class="footer" wx:if="{{!reviewMode && packages.length}}"', vip_wxml)

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

    def test_chat_page_login_gate_is_dismissible_and_does_not_block_browsing(self):
        chat_js = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.js').read_text(encoding='utf-8')
        chat_wxml = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxml').read_text(encoding='utf-8')
        chat_wxss = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxss').read_text(encoding='utf-8')
        api_js = (ROOT / 'miniprogram' / 'utils' / 'api.js').read_text(encoding='utf-8')

        self.assertIn('showLoginGate: false', chat_js)
        self.assertIn('loginLoading: false', chat_js)
        self.assertIn('promptLoginForAccountFeature()', chat_js)
        self.assertIn('appendGuestRecordReply(text)', chat_js)
        self.assertIn('this.appendGuestRecordReply(text)', chat_js)
        self.assertIn('handleGateLogin()', chat_js)
        self.assertIn('dismissLoginGate()', chat_js)
        self.assertIn('goHomeFromLoginGate()', chat_js)
        self.assertIn('loginPromptDismissed: false', chat_js)
        self.assertIn('if (this.data.loginPromptDismissed) return', chat_js)
        self.assertNotIn('checkChatLoginGate()', chat_js)
        self.assertNotIn('showLoginGate: !app.globalData.openid', chat_js)
        self.assertNotIn('if (this.data.showLoginGate) return', chat_js)
        self.assertNotIn('已先帮你保留这条记录', chat_js)
        self.assertNotIn('当前版本暂未开放', chat_js)
        self.assertNotIn('app.loginWithWechat().catch(() => {})', api_js)

        self.assertIn('wx:if="{{showLoginGate}}"', chat_wxml)
        self.assertNotIn('login-gate-mask', chat_wxml + chat_wxss)
        self.assertIn('login-gate-panel', chat_wxml + chat_wxss)
        self.assertIn('bindtap="handleGateLogin"', chat_wxml)
        self.assertIn('bindtap="dismissLoginGate"', chat_wxml)
        self.assertIn('bindtap="goHomeFromLoginGate"', chat_wxml)
        self.assertIn('你仍可先浏览和记录基础内容', chat_wxml)
        self.assertIn('立即登录', chat_wxml)
        self.assertIn('暂不登录', chat_wxml)
        self.assertIn('返回首页', chat_wxml)

        self.assertIn('.login-gate-button', chat_wxss)
        self.assertIn('.login-gate-actions', chat_wxss)
        self.assertIn('.login-gate-link', chat_wxss)

    def test_my_page_login_entry_has_decline_and_return_actions(self):
        my_js = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.js').read_text(encoding='utf-8')
        my_wxml = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.wxml').read_text(encoding='utf-8')
        my_wxss = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.wxss').read_text(encoding='utf-8')

        self.assertIn('skipLogin()', my_js)
        self.assertIn('goHome()', my_js)
        self.assertIn('bindtap="skipLogin"', my_wxml)
        self.assertIn('bindtap="goHome"', my_wxml)
        self.assertIn('暂不登录', my_wxml)
        self.assertIn('返回首页', my_wxml)
        self.assertIn('login-actions', my_wxml + my_wxss)


if __name__ == '__main__':
    unittest.main()
