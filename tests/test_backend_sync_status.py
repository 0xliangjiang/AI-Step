import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackendSyncStatusTests(unittest.TestCase):
    def test_backend_exposes_current_user_sync_status_endpoint(self):
        main_py = (ROOT / 'backend' / 'main.py').read_text(encoding='utf-8')

        self.assertIn('class SyncStatusResponse(BaseModel):', main_py)
        self.assertIn('@app.get("/api/user/sync-status", response_model=SyncStatusResponse)', main_py)
        self.assertIn('from scheduler import scheduler', main_py)
        self.assertIn('scheduler.get_task(user_key)', main_py)
        self.assertIn('db.query(StepRecord)', main_py)
        self.assertIn('"next_sync_at"', main_py)
        self.assertIn('"logs"', main_py)

    def test_scheduler_persists_recent_sync_records_for_hidden_status_page(self):
        scheduler_py = (ROOT / 'backend' / 'scheduler.py').read_text(encoding='utf-8')

        self.assertIn('from models import ScheduledTask, User, SessionLocal, get_db_session, StepRecord', scheduler_py)
        self.assertIn('db.add(StepRecord(', scheduler_py)
        self.assertIn('"scheduled_sync"', scheduler_py)
        self.assertIn('execution_mode', scheduler_py)


if __name__ == '__main__':
    unittest.main()
