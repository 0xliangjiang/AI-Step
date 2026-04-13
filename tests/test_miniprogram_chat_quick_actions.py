import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiniProgramChatQuickActionTests(unittest.TestCase):
    def test_chat_quick_actions_put_share_first_and_use_static_replies(self):
        chat_js = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.js').read_text(encoding='utf-8')
        chat_wxml = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxml').read_text(encoding='utf-8')

        self.assertIn('const QUICK_ACTION_ITEMS = [', chat_js)
        self.assertIn("key: 'share_sport'", chat_js)
        self.assertIn('const STATIC_QUICK_ACTION_RESPONSES = {', chat_js)
        self.assertIn("share_sport'", chat_js)
        self.assertIn('appendStaticQuickReply(action)', chat_js)
        self.assertIn('if (action === \'share_sport\') {', chat_js)
        self.assertNotIn('this.setData({ inputText: action }, () => {\n      this.sendMessage()\n    })', chat_js)

        share_pos = chat_js.find("key: 'share_sport'")
        record_pos = chat_js.find("key: 'record_today'")
        health_pos = chat_js.find("key: 'health_today'")
        self.assertIn('wx:for="{{quickActions}}"', chat_wxml)
        self.assertGreaterEqual(share_pos, 0)
        self.assertGreaterEqual(record_pos, 0)
        self.assertGreaterEqual(health_pos, 0)
        self.assertLess(share_pos, record_pos)
        self.assertLess(share_pos, health_pos)
        self.assertIn('运动记录工具', chat_wxml)
        self.assertIn('这里可以帮你整理今天的运动记录、查看近期数据，并快捷发起运动分享', chat_wxml)


if __name__ == '__main__':
    unittest.main()
