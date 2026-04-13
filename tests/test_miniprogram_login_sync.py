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
        self.assertIn('wx.getStorageSync(PACKAGE_CACHE_KEY)', vip_js)
        self.assertIn('wx.setStorageSync(PACKAGE_CACHE_KEY, packages)', vip_js)
        self.assertIn('usingCachedPackages', vip_js)
        self.assertIn('refreshPackages()', vip_js)
        self.assertIn('套餐暂时没加载出来', vip_wxml)
        self.assertIn('重新加载', vip_wxml)


if __name__ == '__main__':
    unittest.main()
