import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BackendDockerfileTests(unittest.TestCase):
    def test_backend_dockerfile_does_not_override_apt_source_to_aliyun(self):
        dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
        self.assertNotIn("/etc/apt/sources.list.d/debian.sources", dockerfile)
        self.assertNotIn("sed -i 's/deb.debian.org/mirrors.aliyun.com/g'", dockerfile)


if __name__ == "__main__":
    unittest.main()
