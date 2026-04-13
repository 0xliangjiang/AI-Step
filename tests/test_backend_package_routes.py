import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackendPackageRouteTests(unittest.TestCase):
    def test_backend_exposes_alias_route_for_package_list(self):
        main_py = (ROOT / 'backend' / 'main.py').read_text(encoding='utf-8')

        self.assertIn('@app.get("/api/packages", response_model=PackageResponse)', main_py)
        self.assertIn('@app.get("/api/vip/packages", response_model=PackageResponse)', main_py)
        self.assertIn('@app.get("/api/membership/options", response_model=PackageResponse)', main_py)


if __name__ == '__main__':
    unittest.main()
