import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiniProgramAuditCopyTests(unittest.TestCase):
    def test_frontend_copy_avoids_high_risk_ai_and_coaching_terms(self):
        index_wxml = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.wxml').read_text(encoding='utf-8')
        index_js = (ROOT / 'miniprogram' / 'pages' / 'index' / 'index.js').read_text(encoding='utf-8')
        vip_wxml = (ROOT / 'miniprogram' / 'pages' / 'vip' / 'vip.wxml').read_text(encoding='utf-8')
        chat_js = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.js').read_text(encoding='utf-8')
        my_wxml = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.wxml').read_text(encoding='utf-8')

        for text in [
            'AI陪练', '今日陪练', '更懂你', '陪练会员', '建议与提醒', '立即解锁', '正在为你解锁', '陪练套餐'
        ]:
            self.assertNotIn(text, index_wxml + vip_wxml + chat_js + my_wxml)

        self.assertIn('今日记录', index_wxml)
        self.assertIn('记录分析', index_wxml)
        self.assertNotIn('登录后可同步保存记录，并查看每一次小进步', index_wxml)
        self.assertNotIn('微信一键登录', index_wxml)
        self.assertNotIn('获取更适合你的运动记录参考', index_js)

        self.assertIn('开通会员服务', vip_wxml)
        self.assertIn('把运动记录和同步体验升级', vip_wxml)
        self.assertIn('专属记录参考与同步说明', vip_wxml)
        self.assertIn('立即开通 ¥', vip_wxml)
        self.assertIn('先选一个会员套餐', vip_wxml)

        self.assertIn('如果你想看跑步内容参考', chat_js)
        self.assertIn('添加工具回复', chat_js)
        self.assertIn('开通会员查看更多功能', my_wxml)


if __name__ == '__main__':
    unittest.main()
