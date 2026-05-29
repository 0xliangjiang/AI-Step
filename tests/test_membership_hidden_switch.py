import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MembershipHiddenSwitchTests(unittest.TestCase):
    def test_backend_has_independent_hide_membership_flag(self):
        config_py = (ROOT / 'backend' / 'config.py').read_text(encoding='utf-8')

        self.assertIn('HIDE_MEMBERSHIP = os.getenv("HIDE_MEMBERSHIP"', config_py)

    def test_backend_exposes_hide_membership_and_gates_only_membership(self):
        main_py = (ROOT / 'backend' / 'main.py').read_text(encoding='utf-8')

        # 导入与下发
        self.assertIn('REVIEW_MODE, HIDE_MEMBERSHIP', main_py)
        self.assertIn('"hide_membership": HIDE_MEMBERSHIP', main_py)

        # 合并判定 helper
        self.assertIn('def _membership_hidden() -> bool:', main_py)
        self.assertIn('return REVIEW_MODE or HIDE_MEMBERSHIP', main_py)

        # 聊天接口只受 REVIEW_MODE 控制，不被会员开关禁用
        # 取聊天函数体（PEP8 两空行分隔，故按三换行切出单个函数）
        chat_body = main_py.split('async def chat(request: ChatRequest):')[1].split('\n\n\n')[0]
        self.assertIn('if REVIEW_MODE:', chat_body)
        self.assertNotIn('_membership_hidden()', chat_body)

        # 会员/付费/广告接口走合并判定
        self.assertIn('async def _build_package_response():\n    if _membership_hidden():', main_py)
        self.assertIn('async def watch_ad(request: WatchAdRequest):\n    """观看广告奖励会员天数"""\n    if _membership_hidden():', main_py)

    def test_app_provides_is_membership_hidden_helper(self):
        app_js = (ROOT / 'miniprogram' / 'app.js').read_text(encoding='utf-8')

        self.assertIn('hideMembership: false', app_js)
        self.assertIn('const hideMembership = !!data.hide_membership', app_js)
        self.assertIn('isMembershipHidden() {', app_js)
        self.assertIn('config.reviewMode || config.hideMembership', app_js)

    def test_index_page_hides_membership_status_when_switch_on(self):
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')
        index_wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')

        self.assertIn('hideMembership: false', index_js)
        self.assertIn('hideMembership: app.isMembershipHidden()', index_js)
        self.assertIn('wx:if="{{isVip && !hideMembership}}"', index_wxml)
        self.assertIn('class="status-bar" wx:if="{{!hideMembership}}"', index_wxml)
        # 开始打卡入口（通向聊天）不受会员开关影响
        self.assertIn('class="action-section" wx:if="{{!reviewMode}}"', index_wxml)

    def test_my_page_hides_membership_blocks_when_switch_on(self):
        my_js = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.js').read_text(encoding='utf-8')
        my_wxml = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.wxml').read_text(encoding='utf-8')

        self.assertIn('hideMembership: false', my_js)
        self.assertIn('hideMembership: app.isMembershipHidden()', my_js)
        self.assertIn('if (this.data.reviewMode || this.data.hideMembership) {', my_js)
        self.assertIn('class="account-stats" wx:if="{{isLoggedIn && !hideMembership}}"', my_wxml)
        self.assertIn('class="section" wx:if="{{isLoggedIn && !hideMembership}}"', my_wxml)

    def test_vip_page_hides_when_membership_switch_on(self):
        vip_js = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.js').read_text(encoding='utf-8')

        self.assertIn('app.isReviewMode() || app.isMembershipHidden()', vip_js)

    def test_chat_modal_suppressed_when_membership_hidden(self):
        chat_js = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.js').read_text(encoding='utf-8')

        self.assertIn('if (app.isMembershipHidden && app.isMembershipHidden()) return', chat_js)


if __name__ == '__main__':
    unittest.main()
