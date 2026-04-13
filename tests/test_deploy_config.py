import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeployConfigTests(unittest.TestCase):
    def test_backend_uses_host_network_mode(self):
        compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("backend:", compose_text)
        self.assertIn("network_mode: host", compose_text)

    def test_frontend_proxies_api_to_host_gateway(self):
        nginx_text = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")
        self.assertIn("proxy_pass http://host.docker.internal:8000/api/;", nginx_text)

    def test_frontend_has_host_gateway_mapping(self):
        compose_text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("extra_hosts:", compose_text)
        self.assertIn("- \"host.docker.internal:host-gateway\"", compose_text)


if __name__ == "__main__":
    unittest.main()
