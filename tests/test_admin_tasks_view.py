import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AdminTasksViewTests(unittest.TestCase):
    def test_admin_tasks_view_shows_scheduler_diagnostics(self):
        content = (ROOT / "frontend" / "src" / "views" / "AdminTasks.vue").read_text(encoding="utf-8")
        self.assertIn("上次成功", content)
        self.assertIn("连续失败", content)
        self.assertIn("最近错误", content)


if __name__ == "__main__":
    unittest.main()
