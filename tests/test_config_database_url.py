import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import config as config_module


class ConfigDatabaseUrlTests(unittest.TestCase):
    def test_build_database_url_escapes_special_characters_in_password(self):
        url = config_module.build_database_url(
            host="49.235.155.175",
            port=3306,
            user="root",
            password="Abc@123:/#%",
            database="ai_step",
        )

        rendered = url.render_as_string(hide_password=False)
        self.assertIn("mysql+pymysql://root:Abc%40123%3A%2F%23%25@49.235.155.175:3306/ai_step", rendered)


if __name__ == "__main__":
    unittest.main()
