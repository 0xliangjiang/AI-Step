import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ScheduledTaskRangeToolTests(unittest.TestCase):
    def test_ai_tool_schema_accepts_daily_target_range(self):
        skills_py = (ROOT / "backend" / "skills.py").read_text(encoding="utf-8")

        self.assertIn('"min_target_steps"', skills_py)
        self.assertIn('"max_target_steps"', skills_py)
        self.assertIn("每天xx到xx步", skills_py)
        self.assertIn('arguments.get("min_target_steps")', skills_py)
        self.assertIn('arguments.get("max_target_steps")', skills_py)

    def test_system_prompt_teaches_range_scheduled_tasks(self):
        config_py = (ROOT / "backend" / "config.py").read_text(encoding="utf-8")

        self.assertIn("每天8点到21点完成30000到50000步", config_py)
        self.assertIn("系统每天会在范围内随机选择当天目标", config_py)


if __name__ == "__main__":
    unittest.main()
