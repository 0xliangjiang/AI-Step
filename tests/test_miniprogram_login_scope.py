import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiniProgramLoginScopeTests(unittest.TestCase):
    def test_login_hoists_merged_profile_outside_nested_callbacks(self):
        app_js = (ROOT / 'miniprogram' / 'app.js').read_text(encoding='utf-8')

        self.assertIn("const cachedProfile = wx.getStorageSync('userProfile') || null", app_js)
        self.assertIn("const mergedProfile = cachedProfile ? mergeUserProfile(cachedProfile, null) : null", app_js)
        self.assertLess(
            app_js.index("const mergedProfile = cachedProfile ? mergeUserProfile(cachedProfile, null) : null"),
            app_js.index('wx.login({')
        )


if __name__ == '__main__':
    unittest.main()
