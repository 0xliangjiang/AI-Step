import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MiniProgramThemeTests(unittest.TestCase):
    def test_app_theme_uses_warm_sport_palette(self):
        app_json = json.loads((ROOT / "miniprogram" / "app.json").read_text(encoding="utf-8"))
        app_wxss = (ROOT / "miniprogram" / "app.wxss").read_text(encoding="utf-8")

        self.assertEqual("#FF8A3D", app_json["window"]["navigationBarBackgroundColor"])
        self.assertEqual("#FF8A3D", app_json["tabBar"]["selectedColor"])
        self.assertIn("--brand-sun: #FF8A3D;", app_wxss)
        self.assertIn("--brand-lake: #39B8FF;", app_wxss)
        self.assertIn("--page-cream: #FFF8F0;", app_wxss)


if __name__ == "__main__":
    unittest.main()
