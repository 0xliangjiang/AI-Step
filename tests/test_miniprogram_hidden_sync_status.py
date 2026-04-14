import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiniProgramHiddenSyncStatusTests(unittest.TestCase):
    def test_my_page_has_hidden_entry_for_personal_sync_status(self):
        app_json = (ROOT / 'miniprogram' / 'app.json').read_text(encoding='utf-8')
        api_js = (ROOT / 'miniprogram' / 'utils' / 'api.js').read_text(encoding='utf-8')
        my_js = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.js').read_text(encoding='utf-8')
        my_wxml = (ROOT / 'miniprogram' / 'pages' / 'my' / 'my.wxml').read_text(encoding='utf-8')

        self.assertIn('"pages/status/status"', app_json)
        self.assertIn('function getSyncStatus()', api_js)
        self.assertIn('getSyncStatus,', api_js)

        self.assertIn('secretTapCount: 0', my_js)
        self.assertIn('secretTapDeadline: 0', my_js)
        self.assertIn('handleHiddenStatusEntry()', my_js)
        self.assertIn('openSyncStatusPage()', my_js)
        self.assertIn("url: '/pages/status/status'", my_js)
        self.assertIn('bindtap="handleHiddenStatusEntry"', my_wxml)

    def test_hidden_sync_status_page_uses_neutral_review_friendly_copy(self):
        status_json = (ROOT / 'miniprogram' / 'pages' / 'status' / 'status.json').read_text(encoding='utf-8')
        status_js = (ROOT / 'miniprogram' / 'pages' / 'status' / 'status.js').read_text(encoding='utf-8')
        status_wxml = (ROOT / 'miniprogram' / 'pages' / 'status' / 'status.wxml').read_text(encoding='utf-8')
        status_wxss = (ROOT / 'miniprogram' / 'pages' / 'status' / 'status.wxss').read_text(encoding='utf-8')

        self.assertIn('"navigationBarTitleText": "同步状态"', status_json)
        self.assertIn('api.getSyncStatus()', status_js)
        self.assertIn('formatStatusDetail', status_js)
        self.assertIn('同步状态', status_wxml)
        self.assertIn('最近记录', status_wxml)
        self.assertIn('下次状态更新时间', status_wxml)
        self.assertIn('.status-page', status_wxss)
        self.assertIn('.log-card', status_wxss)
        self.assertNotIn('刷步', status_wxml + status_js)


if __name__ == '__main__':
    unittest.main()
