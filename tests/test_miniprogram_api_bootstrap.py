import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiniProgramApiBootstrapTests(unittest.TestCase):
    def test_api_module_does_not_capture_app_at_module_load(self):
        api_js = (ROOT / 'miniprogram' / 'utils' / 'api.js').read_text(encoding='utf-8')

        self.assertNotIn('const app = getApp()', api_js)
        self.assertIn('function getAppInstance()', api_js)
        self.assertIn('const app = getAppInstance()', api_js)
        self.assertIn("const globalData = (app && app.globalData) || {}", api_js)


if __name__ == '__main__':
    unittest.main()
