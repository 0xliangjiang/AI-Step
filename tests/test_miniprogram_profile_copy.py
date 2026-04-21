import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiniProgramProfileCopyTests(unittest.TestCase):
    def test_avatar_rendering_has_explicit_fallback_guard(self):
        profile_utils = (ROOT / 'miniprogram' / 'utils' / 'profile.js').read_text(encoding='utf-8')
        index_wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')
        my_wxml = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.wxml').read_text(encoding='utf-8')
        chat_wxml = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxml').read_text(encoding='utf-8')
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')
        my_js = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.js').read_text(encoding='utf-8')
        chat_js = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.js').read_text(encoding='utf-8')

        self.assertIn('function normalizeAvatarUrl', profile_utils)
        self.assertIn('wx:if="{{displayAvatarUrl}}"', index_wxml)
        self.assertIn('binderror="onAvatarError"', index_wxml)
        self.assertIn('wx:if="{{displayAvatarUrl}}"', my_wxml)
        self.assertIn('binderror="onAvatarError"', my_wxml)
        self.assertIn("wx:if=\"{{item.role === 'user' && displayAvatarUrl}}\"", chat_wxml)
        self.assertIn('binderror="onAvatarError"', chat_wxml)
        self.assertIn('displayAvatarUrl', index_js)
        self.assertIn('onAvatarError()', index_js)
        self.assertIn('displayAvatarUrl', my_js)
        self.assertIn('onAvatarError()', my_js)
        self.assertIn('displayAvatarUrl', chat_js)
        self.assertIn('onAvatarError()', chat_js)

    def test_chat_loading_state_shows_processing_hint(self):
        chat_js = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.js').read_text(encoding='utf-8')
        chat_wxml = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxml').read_text(encoding='utf-8')

        self.assertIn("loadingHint: '正在处理中，一般会在 2 分钟内返回'", chat_js)
        self.assertIn('{{loadingHint}}', chat_wxml)

    def test_home_and_vip_copy_uses_friendly_neutral_wording(self):
        index_wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')
        vip_wxml = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.wxml').read_text(encoding='utf-8')
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')

        self.assertIn('今天想怎么动一动？', index_wxml)
        self.assertIn('轻松打卡', index_wxml)
        self.assertIn('开始今日打卡', index_wxml)
        self.assertIn('今天动一点，也是在认真照顾自己', index_wxml)
        self.assertNotIn('欢迎回来，开始今天的轻运动', index_wxml)
        self.assertNotIn('记录每一次小进步', index_js)
        self.assertIn('开通会员服务', vip_wxml)
        self.assertIn('把运动记录和同步体验升级', vip_wxml)
        self.assertIn('不限次查看运动复盘', vip_wxml)
        self.assertIn('专属记录参考与同步说明', vip_wxml)

    def test_vip_page_uses_featured_mobile_card_layout(self):
        vip_wxml = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.wxml').read_text(encoding='utf-8')
        vip_wxss = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.wxss').read_text(encoding='utf-8')

        self.assertIn('package-spotlight', vip_wxml)
        self.assertIn('package-hero', vip_wxml)
        self.assertIn('package-meta-row', vip_wxml)
        self.assertIn('package-price-note', vip_wxml)
        self.assertIn('footer-summary', vip_wxml)
        self.assertIn('.package-spotlight', vip_wxss)
        self.assertIn('.package-hero', vip_wxss)
        self.assertIn('.package-price-note', vip_wxss)
        self.assertIn('.footer-summary', vip_wxss)
        self.assertIn('@media (max-width: 360px)', vip_wxss)


if __name__ == '__main__':
    unittest.main()
