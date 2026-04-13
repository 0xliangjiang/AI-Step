import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackendDockerfileTests(unittest.TestCase):
    def test_backend_dockerfile_uses_tuna_https_for_apt_sources(self):
        dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("/etc/apt/sources.list.d/debian.sources", dockerfile)
        self.assertIn("https://mirrors.tuna.tsinghua.edu.cn/debian", dockerfile)
        self.assertIn("https://mirrors.tuna.tsinghua.edu.cn/debian-security", dockerfile)


if __name__ == "__main__":
    unittest.main()
