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


if __name__ == '__main__':
    unittest.main()
